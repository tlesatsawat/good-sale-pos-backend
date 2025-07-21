import requests
import json
import logging
from datetime import datetime
from typing import Dict, Optional
import base64
import os

class LINEIntegration:
    def __init__(self, channel_access_token: str = None, webhook_url: str = None):
        self.logger = logging.getLogger(__name__)
        self.channel_access_token = channel_access_token or os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        self.webhook_url = webhook_url or os.getenv('LINE_WEBHOOK_URL')
        self.api_base_url = 'https://api.line.me/v2/bot'
        
        # Headers สำหรับ LINE API
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.channel_access_token}' if self.channel_access_token else ''
        }
    
    def send_payment_notification(self, user_id: str, payment_data: Dict) -> bool:
        """ส่งการแจ้งเตือนการชำระเงินไป LINE"""
        try:
            if not self.channel_access_token:
                self.logger.warning("LINE Channel Access Token not configured")
                return self._simulate_line_notification(payment_data)
            
            # สร้างข้อความแจ้งเตือน
            message = self._create_payment_message(payment_data)
            
            # ส่งข้อความ
            payload = {
                'to': user_id,
                'messages': [message]
            }
            
            response = requests.post(
                f'{self.api_base_url}/message/push',
                headers=self.headers,
                data=json.dumps(payload)
            )
            
            if response.status_code == 200:
                self.logger.info(f"Payment notification sent to LINE user: {user_id}")
                return True
            else:
                self.logger.error(f"Failed to send LINE notification: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending LINE notification: {e}")
            return False
    
    def send_receipt_image(self, user_id: str, receipt_image_path: str, payment_data: Dict) -> bool:
        """ส่งรูปใบเสร็จไป LINE"""
        try:
            if not self.channel_access_token:
                self.logger.warning("LINE Channel Access Token not configured")
                return self._simulate_line_notification(payment_data, with_image=True)
            
            # อัปโหลดรูปภาพ
            image_url = self._upload_image_to_line(receipt_image_path)
            if not image_url:
                return False
            
            # สร้างข้อความพร้อมรูปภาพ
            messages = [
                {
                    'type': 'image',
                    'originalContentUrl': image_url,
                    'previewImageUrl': image_url
                },
                self._create_payment_message(payment_data)
            ]
            
            payload = {
                'to': user_id,
                'messages': messages
            }
            
            response = requests.post(
                f'{self.api_base_url}/message/push',
                headers=self.headers,
                data=json.dumps(payload)
            )
            
            if response.status_code == 200:
                self.logger.info(f"Receipt image sent to LINE user: {user_id}")
                return True
            else:
                self.logger.error(f"Failed to send receipt image: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending receipt image: {e}")
            return False
    
    def send_qr_slip_notification(self, user_id: str, slip_image_data: str, payment_data: Dict) -> bool:
        """ส่งการแจ้งเตือนพร้อมสลิป QR Code ไป LINE"""
        try:
            if not self.channel_access_token:
                self.logger.warning("LINE Channel Access Token not configured")
                return self._simulate_qr_slip_notification(payment_data)
            
            # บันทึกรูปสลิปชั่วคราว
            slip_path = self._save_slip_image(slip_image_data, payment_data.get('order_id', 'unknown'))
            
            # ส่งรูปสลิปและข้อมูลการชำระเงิน
            success = self.send_receipt_image(user_id, slip_path, payment_data)
            
            # ลบไฟล์ชั่วคราว
            if os.path.exists(slip_path):
                os.remove(slip_path)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending QR slip notification: {e}")
            return False
    
    def _create_payment_message(self, payment_data: Dict) -> Dict:
        """สร้างข้อความแจ้งเตือนการชำระเงิน"""
        store_name = payment_data.get('store_name', 'GOOD SALE POS')
        order_id = payment_data.get('order_id', 'N/A')
        total_amount = payment_data.get('total_amount', 0)
        payment_method = payment_data.get('payment_method', 'QR Code')
        timestamp = payment_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        message_text = f"""🧾 การชำระเงินสำเร็จ
        
🏪 ร้าน: {store_name}
📋 Order ID: {order_id}
💰 จำนวนเงิน: {total_amount:,.2f} บาท
💳 วิธีชำระ: {payment_method}
⏰ เวลา: {timestamp}

ขอบคุณที่ใช้บริการ! 🙏"""
        
        return {
            'type': 'text',
            'text': message_text
        }
    
    def _upload_image_to_line(self, image_path: str) -> Optional[str]:
        """อัปโหลดรูปภาพไป LINE (จำลอง)"""
        try:
            # ในการใช้งานจริง ต้องอัปโหลดไปยัง server ที่ LINE เข้าถึงได้
            # ที่นี่จะ return URL จำลอง
            return f"https://example.com/images/{os.path.basename(image_path)}"
            
        except Exception as e:
            self.logger.error(f"Error uploading image: {e}")
            return None
    
    def _save_slip_image(self, image_data: str, order_id: str) -> str:
        """บันทึกรูปสลิปชั่วคราว"""
        try:
            # แปลง base64 เป็นไฟล์รูปภาพ
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            
            # สร้างชื่อไฟล์
            filename = f"slip_{order_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = os.path.join('/tmp', filename)
            
            # บันทึกไฟล์
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error saving slip image: {e}")
            return ""
    
    def _simulate_line_notification(self, payment_data: Dict, with_image: bool = False) -> bool:
        """จำลองการส่งการแจ้งเตือนไป LINE"""
        try:
            message = self._create_payment_message(payment_data)
            
            # บันทึกลงไฟล์สำหรับการทดสอบ
            log_data = {
                'timestamp': datetime.now().isoformat(),
                'type': 'line_notification',
                'with_image': with_image,
                'message': message,
                'payment_data': payment_data
            }
            
            log_filename = f"line_notification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(log_filename, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"LINE notification simulated and saved to: {log_filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error simulating LINE notification: {e}")
            return False
    
    def _simulate_qr_slip_notification(self, payment_data: Dict) -> bool:
        """จำลองการส่งสลิป QR Code ไป LINE"""
        try:
            log_data = {
                'timestamp': datetime.now().isoformat(),
                'type': 'qr_slip_notification',
                'payment_data': payment_data,
                'message': 'QR Code slip uploaded and notification sent to LINE'
            }
            
            log_filename = f"qr_slip_notification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(log_filename, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"QR slip notification simulated and saved to: {log_filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error simulating QR slip notification: {e}")
            return False
    
    def verify_webhook(self, signature: str, body: str) -> bool:
        """ตรวจสอบ webhook signature จาก LINE"""
        try:
            import hmac
            import hashlib
            
            if not self.webhook_url:
                return True  # Skip verification in development
            
            channel_secret = os.getenv('LINE_CHANNEL_SECRET', '')
            if not channel_secret:
                return True
            
            hash_value = hmac.new(
                channel_secret.encode('utf-8'),
                body.encode('utf-8'),
                hashlib.sha256
            ).digest()
            
            expected_signature = base64.b64encode(hash_value).decode('utf-8')
            return signature == expected_signature
            
        except Exception as e:
            self.logger.error(f"Error verifying webhook: {e}")
            return False
    
    def handle_webhook_event(self, event_data: Dict) -> bool:
        """จัดการ webhook event จาก LINE"""
        try:
            events = event_data.get('events', [])
            
            for event in events:
                event_type = event.get('type')
                
                if event_type == 'message':
                    self._handle_message_event(event)
                elif event_type == 'follow':
                    self._handle_follow_event(event)
                elif event_type == 'unfollow':
                    self._handle_unfollow_event(event)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling webhook event: {e}")
            return False
    
    def _handle_message_event(self, event: Dict):
        """จัดการ message event"""
        user_id = event.get('source', {}).get('userId')
        message = event.get('message', {})
        message_text = message.get('text', '')
        
        self.logger.info(f"Received message from {user_id}: {message_text}")
        
        # ตอบกลับข้อความอัตโนมัติ
        if message_text.lower() in ['สวัสดี', 'hello', 'hi']:
            self._send_welcome_message(user_id)
    
    def _handle_follow_event(self, event: Dict):
        """จัดการ follow event"""
        user_id = event.get('source', {}).get('userId')
        self.logger.info(f"User {user_id} followed the bot")
        self._send_welcome_message(user_id)
    
    def _handle_unfollow_event(self, event: Dict):
        """จัดการ unfollow event"""
        user_id = event.get('source', {}).get('userId')
        self.logger.info(f"User {user_id} unfollowed the bot")
    
    def _send_welcome_message(self, user_id: str):
        """ส่งข้อความต้อนรับ"""
        welcome_message = {
            'type': 'text',
            'text': 'สวัสดีครับ! ยินดีต้อนรับสู่ GOOD SALE POS 🎉\n\nคุณจะได้รับการแจ้งเตือนการชำระเงินและใบเสร็จผ่าน LINE นี้ครับ'
        }
        
        payload = {
            'to': user_id,
            'messages': [welcome_message]
        }
        
        try:
            if self.channel_access_token:
                response = requests.post(
                    f'{self.api_base_url}/message/push',
                    headers=self.headers,
                    data=json.dumps(payload)
                )
                
                if response.status_code == 200:
                    self.logger.info(f"Welcome message sent to {user_id}")
                else:
                    self.logger.error(f"Failed to send welcome message: {response.status_code}")
            else:
                self.logger.info(f"Welcome message simulated for {user_id}")
                
        except Exception as e:
            self.logger.error(f"Error sending welcome message: {e}")

