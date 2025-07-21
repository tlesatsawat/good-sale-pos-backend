from flask import Blueprint, request, jsonify
import logging
from qr_payment import QRPaymentManager
from line_integration import LINEIntegration

payment_bp = Blueprint('payment', __name__)
logger = logging.getLogger(__name__)

# สร้าง instances
qr_payment = QRPaymentManager()
line_integration = LINEIntegration()

@payment_bp.route('/generate-qr', methods=['POST'])
def generate_qr_payment():
    """สร้าง QR Code สำหรับการชำระเงิน"""
    try:
        data = request.get_json()
        amount = data.get('amount', 0)
        order_id = data.get('order_id')
        store_name = data.get('store_name', 'GOOD SALE POS')
        
        if amount <= 0:
            return jsonify({
                'success': False,
                'message': 'จำนวนเงินต้องมากกว่า 0'
            }), 400
        
        # สร้าง QR Code
        result = qr_payment.generate_promptpay_qr(
            amount=amount,
            ref1=order_id,
            ref2=store_name[:10]  # จำกัดความยาว
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถสร้าง QR Code ได้'
            }), 500
            
    except Exception as e:
        logger.error(f"Error generating QR payment: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการสร้าง QR Code'
        }), 500

@payment_bp.route('/verify-payment', methods=['POST'])
def verify_payment():
    """ตรวจสอบการชำระเงิน"""
    try:
        data = request.get_json()
        payment_id = data.get('payment_id')
        slip_image_data = data.get('slip_image')
        
        if not payment_id:
            return jsonify({
                'success': False,
                'message': 'ไม่พบ Payment ID'
            }), 400
        
        # ตรวจสอบการชำระเงิน
        result = qr_payment.verify_payment(payment_id, slip_image_data)
        
        return jsonify({
            'success': result['success'],
            'data': result if result['success'] else None,
            'message': result.get('error') if not result['success'] else 'ตรวจสอบการชำระเงินสำเร็จ'
        })
        
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการตรวจสอบการชำระเงิน'
        }), 500

@payment_bp.route('/upload-slip', methods=['POST'])
def upload_payment_slip():
    """อัปโหลดสลิปการชำระเงินและส่งไป LINE"""
    try:
        data = request.get_json()
        payment_id = data.get('payment_id')
        slip_image_data = data.get('slip_image')
        order_data = data.get('order_data', {})
        line_user_id = data.get('line_user_id')
        
        if not payment_id or not slip_image_data:
            return jsonify({
                'success': False,
                'message': 'ไม่พบข้อมูลที่จำเป็น'
            }), 400
        
        # ตรวจสอบการชำระเงิน
        verification_result = qr_payment.verify_payment(payment_id, slip_image_data)
        
        if not verification_result['success']:
            return jsonify({
                'success': False,
                'message': verification_result.get('error', 'การตรวจสอบการชำระเงินไม่สำเร็จ')
            })
        
        # เตรียมข้อมูลสำหรับส่งไป LINE
        payment_data = {
            'store_name': order_data.get('store_name', 'GOOD SALE POS'),
            'order_id': order_data.get('order_id', payment_id),
            'total_amount': verification_result.get('amount', 0),
            'payment_method': 'QR Code PromptPay',
            'timestamp': verification_result.get('verified_at')
        }
        
        # ส่งการแจ้งเตือนไป LINE
        line_success = False
        if line_user_id:
            line_success = line_integration.send_qr_slip_notification(
                line_user_id, 
                slip_image_data, 
                payment_data
            )
        else:
            # ถ้าไม่มี LINE user ID ให้จำลองการส่ง
            line_success = line_integration._simulate_qr_slip_notification(payment_data)
        
        return jsonify({
            'success': True,
            'data': {
                'payment_verified': True,
                'line_notification_sent': line_success,
                'payment_data': payment_data
            },
            'message': 'อัปโหลดสลิปและส่งการแจ้งเตือนเรียบร้อยแล้ว'
        })
        
    except Exception as e:
        logger.error(f"Error uploading payment slip: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการอัปโหลดสลิป'
        }), 500

@payment_bp.route('/status/<payment_id>', methods=['GET'])
def get_payment_status(payment_id):
    """ดึงสถานะการชำระเงิน"""
    try:
        result = qr_payment.get_payment_status(payment_id)
        
        return jsonify({
            'success': result['success'],
            'data': result if result['success'] else None,
            'message': result.get('error') if not result['success'] else None
        })
        
    except Exception as e:
        logger.error(f"Error getting payment status: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการดึงสถานะการชำระเงิน'
        }), 500

@payment_bp.route('/cancel/<payment_id>', methods=['POST'])
def cancel_payment(payment_id):
    """ยกเลิกการชำระเงิน"""
    try:
        result = qr_payment.cancel_payment(payment_id)
        
        return jsonify({
            'success': result['success'],
            'data': result if result['success'] else None,
            'message': result.get('error') if not result['success'] else 'ยกเลิกการชำระเงินเรียบร้อยแล้ว'
        })
        
    except Exception as e:
        logger.error(f"Error cancelling payment: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการยกเลิกการชำระเงิน'
        }), 500

@payment_bp.route('/line/webhook', methods=['POST'])
def line_webhook():
    """รับ webhook จาก LINE"""
    try:
        # ตรวจสอบ signature
        signature = request.headers.get('X-Line-Signature', '')
        body = request.get_data(as_text=True)
        
        if not line_integration.verify_webhook(signature, body):
            return jsonify({'error': 'Invalid signature'}), 400
        
        # จัดการ event
        event_data = request.get_json()
        success = line_integration.handle_webhook_event(event_data)
        
        if success:
            return jsonify({'status': 'ok'})
        else:
            return jsonify({'error': 'Failed to handle event'}), 500
            
    except Exception as e:
        logger.error(f"Error handling LINE webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@payment_bp.route('/line/send-notification', methods=['POST'])
def send_line_notification():
    """ส่งการแจ้งเตือนไป LINE"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        payment_data = data.get('payment_data', {})
        
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'ไม่พบ LINE User ID'
            }), 400
        
        # ส่งการแจ้งเตือน
        success = line_integration.send_payment_notification(user_id, payment_data)
        
        return jsonify({
            'success': success,
            'message': 'ส่งการแจ้งเตือนเรียบร้อยแล้ว' if success else 'ไม่สามารถส่งการแจ้งเตือนได้'
        })
        
    except Exception as e:
        logger.error(f"Error sending LINE notification: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการส่งการแจ้งเตือน'
        }), 500

@payment_bp.route('/cleanup-expired', methods=['POST'])
def cleanup_expired_payments():
    """ลบข้อมูลการชำระเงินที่หมดอายุ"""
    try:
        count = qr_payment.cleanup_expired_payments()
        
        return jsonify({
            'success': True,
            'data': {
                'expired_payments_count': count
            },
            'message': f'ลบข้อมูลการชำระเงินที่หมดอายุ {count} รายการ'
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up expired payments: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการลบข้อมูล'
        }), 500

