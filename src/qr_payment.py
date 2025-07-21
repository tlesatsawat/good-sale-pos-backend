import qrcode
import io
import base64
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
import requests

class QRPaymentManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pending_payments = {}  # เก็บข้อมูลการชำระเงินที่รอดำเนินการ
        
        # ข้อมูล PromptPay (ในการใช้งานจริงควรเก็บใน environment variables)
        self.promptpay_id = "0123456789"  # เบอร์โทรหรือเลขประจำตัวประชาชน
        self.merchant_name = "GOOD SALE POS"
    
    def generate_promptpay_qr(self, amount: float, ref1: str = None, ref2: str = None) -> Dict:
        """สร้าง QR Code สำหรับ PromptPay"""
        try:
            # สร้าง payload สำหรับ PromptPay
            payload = self._create_promptpay_payload(amount, ref1, ref2)
            
            # สร้าง QR Code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(payload)
            qr.make(fit=True)
            
            # สร้างรูปภาพ QR Code
            img = qr.make_image(fill_color="black", back_color="white")
            
            # แปลงเป็น base64
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            
            # สร้าง payment ID
            payment_id = str(uuid.uuid4())
            
            # เก็บข้อมูลการชำระเงิน
            payment_data = {
                'payment_id': payment_id,
                'amount': amount,
                'ref1': ref1,
                'ref2': ref2,
                'payload': payload,
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(minutes=15)).isoformat()
            }
            
            self.pending_payments[payment_id] = payment_data
            
            return {
                'success': True,
                'payment_id': payment_id,
                'qr_code_base64': f"data:image/png;base64,{img_base64}",
                'amount': amount,
                'payload': payload,
                'expires_at': payment_data['expires_at']
            }
            
        except Exception as e:
            self.logger.error(f"Error generating PromptPay QR: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_promptpay_payload(self, amount: float, ref1: str = None, ref2: str = None) -> str:
        """สร้าง payload สำหรับ PromptPay QR Code"""
        try:
            # PromptPay QR Code format (EMV QR Code)
            payload_parts = []
            
            # Payload Format Indicator
            payload_parts.append("000201")
            
            # Point of Initiation Method
            payload_parts.append("010212")
            
            # Merchant Account Information
            merchant_info = f"0016A000000677010111{self._format_promptpay_id(self.promptpay_id)}"
            payload_parts.append(f"29{len(merchant_info):02d}{merchant_info}")
            
            # Merchant Category Code
            payload_parts.append("52044814")
            
            # Transaction Currency (THB = 764)
            payload_parts.append("5303764")
            
            # Transaction Amount
            if amount > 0:
                amount_str = f"{amount:.2f}"
                payload_parts.append(f"54{len(amount_str):02d}{amount_str}")
            
            # Country Code
            payload_parts.append("5802TH")
            
            # Merchant Name
            merchant_name_encoded = self.merchant_name.encode('utf-8')[:25]  # จำกัด 25 bytes
            payload_parts.append(f"59{len(merchant_name_encoded):02d}{merchant_name_encoded.decode('utf-8')}")
            
            # Additional Data Field Template
            additional_data = []
            if ref1:
                ref1_encoded = ref1.encode('utf-8')[:25]
                additional_data.append(f"01{len(ref1_encoded):02d}{ref1_encoded.decode('utf-8')}")
            if ref2:
                ref2_encoded = ref2.encode('utf-8')[:25]
                additional_data.append(f"02{len(ref2_encoded):02d}{ref2_encoded.decode('utf-8')}")
            
            if additional_data:
                additional_data_str = "".join(additional_data)
                payload_parts.append(f"62{len(additional_data_str):02d}{additional_data_str}")
            
            # รวม payload
            payload_without_crc = "".join(payload_parts) + "6304"
            
            # คำนวณ CRC16
            crc = self._calculate_crc16(payload_without_crc)
            
            # payload สมบูรณ์
            complete_payload = payload_without_crc + f"{crc:04X}"
            
            return complete_payload
            
        except Exception as e:
            self.logger.error(f"Error creating PromptPay payload: {e}")
            return ""
    
    def _format_promptpay_id(self, promptpay_id: str) -> str:
        """จัดรูปแบบ PromptPay ID"""
        # ลบอักขระที่ไม่ต้องการ
        clean_id = ''.join(filter(str.isdigit, promptpay_id))
        
        if len(clean_id) == 10:  # เบอร์โทรศัพท์
            return f"0066{clean_id[1:]}"  # แปลง 08xxxxxxxx เป็น 006687xxxxxxx
        elif len(clean_id) == 13:  # เลขประจำตัวประชาชน
            return clean_id
        else:
            return clean_id.ljust(13, '0')  # เติม 0 ให้ครบ 13 หลัก
    
    def _calculate_crc16(self, data: str) -> int:
        """คำนวณ CRC16 สำหรับ PromptPay"""
        crc = 0xFFFF
        polynomial = 0x1021
        
        for byte in data.encode('utf-8'):
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ polynomial
                else:
                    crc <<= 1
                crc &= 0xFFFF
        
        return crc
    
    def verify_payment(self, payment_id: str, slip_image_data: str = None) -> Dict:
        """ตรวจสอบการชำระเงิน"""
        try:
            if payment_id not in self.pending_payments:
                return {
                    'success': False,
                    'error': 'Payment ID not found'
                }
            
            payment_data = self.pending_payments[payment_id]
            
            # ตรวจสอบว่าหมดอายุหรือไม่
            expires_at = datetime.fromisoformat(payment_data['expires_at'])
            if datetime.now() > expires_at:
                return {
                    'success': False,
                    'error': 'Payment expired'
                }
            
            # ในการใช้งานจริง ควรตรวจสอบกับธนาคารหรือ payment gateway
            # ที่นี่จะจำลองการตรวจสอบ
            verification_result = self._simulate_payment_verification(payment_data, slip_image_data)
            
            if verification_result['success']:
                # อัปเดตสถานะการชำระเงิน
                payment_data['status'] = 'completed'
                payment_data['verified_at'] = datetime.now().isoformat()
                payment_data['slip_image'] = slip_image_data
                
                return {
                    'success': True,
                    'payment_id': payment_id,
                    'amount': payment_data['amount'],
                    'status': 'completed',
                    'verified_at': payment_data['verified_at']
                }
            else:
                return verification_result
                
        except Exception as e:
            self.logger.error(f"Error verifying payment: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _simulate_payment_verification(self, payment_data: Dict, slip_image_data: str = None) -> Dict:
        """จำลองการตรวจสอบการชำระเงิน"""
        try:
            # จำลองการตรวจสอบ - ในการใช้งานจริงต้องเชื่อมต่อกับ API ของธนาคาร
            
            # ถ้ามีรูปสลิป ถือว่าชำระเงินแล้ว
            if slip_image_data:
                # บันทึกรูปสลิปสำหรับการตรวจสอบ
                slip_filename = f"slip_{payment_data['payment_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                self._save_slip_image(slip_image_data, slip_filename)
                
                return {
                    'success': True,
                    'verification_method': 'slip_upload',
                    'slip_filename': slip_filename
                }
            
            # จำลองการตรวจสอบอัตโนมัติ (สุ่มผลลัพธ์)
            import random
            if random.random() > 0.2:  # 80% โอกาสสำเร็จ
                return {
                    'success': True,
                    'verification_method': 'automatic',
                    'transaction_ref': f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}"
                }
            else:
                return {
                    'success': False,
                    'error': 'Payment verification failed'
                }
                
        except Exception as e:
            self.logger.error(f"Error in payment verification simulation: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _save_slip_image(self, image_data: str, filename: str) -> bool:
        """บันทึกรูปสลิป"""
        try:
            # แปลง base64 เป็นไฟล์รูปภาพ
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            
            # สร้างโฟลเดอร์ถ้ายังไม่มี
            import os
            slip_dir = 'payment_slips'
            if not os.path.exists(slip_dir):
                os.makedirs(slip_dir)
            
            # บันทึกไฟล์
            filepath = os.path.join(slip_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            self.logger.info(f"Payment slip saved: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving slip image: {e}")
            return False
    
    def get_payment_status(self, payment_id: str) -> Dict:
        """ดึงสถานะการชำระเงิน"""
        try:
            if payment_id not in self.pending_payments:
                return {
                    'success': False,
                    'error': 'Payment ID not found'
                }
            
            payment_data = self.pending_payments[payment_id]
            
            return {
                'success': True,
                'payment_id': payment_id,
                'status': payment_data['status'],
                'amount': payment_data['amount'],
                'created_at': payment_data['created_at'],
                'expires_at': payment_data['expires_at'],
                'verified_at': payment_data.get('verified_at')
            }
            
        except Exception as e:
            self.logger.error(f"Error getting payment status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cancel_payment(self, payment_id: str) -> Dict:
        """ยกเลิกการชำระเงิน"""
        try:
            if payment_id not in self.pending_payments:
                return {
                    'success': False,
                    'error': 'Payment ID not found'
                }
            
            payment_data = self.pending_payments[payment_id]
            
            if payment_data['status'] == 'completed':
                return {
                    'success': False,
                    'error': 'Cannot cancel completed payment'
                }
            
            # อัปเดตสถานะ
            payment_data['status'] = 'cancelled'
            payment_data['cancelled_at'] = datetime.now().isoformat()
            
            return {
                'success': True,
                'payment_id': payment_id,
                'status': 'cancelled'
            }
            
        except Exception as e:
            self.logger.error(f"Error cancelling payment: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_expired_payments(self):
        """ลบข้อมูลการชำระเงินที่หมดอายุ"""
        try:
            current_time = datetime.now()
            expired_payments = []
            
            for payment_id, payment_data in self.pending_payments.items():
                expires_at = datetime.fromisoformat(payment_data['expires_at'])
                if current_time > expires_at and payment_data['status'] == 'pending':
                    expired_payments.append(payment_id)
            
            for payment_id in expired_payments:
                self.pending_payments[payment_id]['status'] = 'expired'
                self.logger.info(f"Payment {payment_id} marked as expired")
            
            return len(expired_payments)
            
        except Exception as e:
            self.logger.error(f"Error cleaning up expired payments: {e}")
            return 0

