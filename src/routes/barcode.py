from flask import Blueprint, request, jsonify
import logging
from barcode_scanner import BarcodeScanner

barcode_bp = Blueprint('barcode', __name__)
logger = logging.getLogger(__name__)

# สร้าง instance ของ BarcodeScanner
scanner = BarcodeScanner()

@barcode_bp.route('/scan-image', methods=['POST'])
def scan_barcode_from_image():
    """สแกนบาร์โค้ดจากรูปภาพ"""
    try:
        data = request.get_json()
        image_data = data.get('image_data')
        
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'ไม่พบข้อมูลรูปภาพ'
            }), 400
        
        # สแกนบาร์โค้ด
        results = scanner.scan_from_image(image_data)
        
        if results:
            # ตรวจสอบความถูกต้องของบาร์โค้ดแรก
            first_result = results[0]
            validation = scanner.validate_barcode(first_result['data'], first_result['type'])
            
            # ดึงข้อมูลสินค้า
            product_info = scanner.get_product_info(first_result['data'])
            
            return jsonify({
                'success': True,
                'data': {
                    'barcodes': results,
                    'validation': validation,
                    'product_info': product_info
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ไม่พบบาร์โค้ดในรูปภาพ'
            })
            
    except Exception as e:
        logger.error(f"Error scanning barcode from image: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการสแกนบาร์โค้ด'
        }), 500

@barcode_bp.route('/scan-file', methods=['POST'])
def scan_barcode_from_file():
    """สแกนบาร์โค้ดจากไฟล์รูปภาพ"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'ไม่พบไฟล์รูปภาพ'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'ไม่ได้เลือกไฟล์'
            }), 400
        
        # บันทึกไฟล์ชั่วคราว
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # สแกนบาร์โค้ด
            results = scanner.scan_from_file(temp_path)
            
            if results:
                # ตรวจสอบความถูกต้องของบาร์โค้ดแรก
                first_result = results[0]
                validation = scanner.validate_barcode(first_result['data'], first_result['type'])
                
                # ดึงข้อมูลสินค้า
                product_info = scanner.get_product_info(first_result['data'])
                
                return jsonify({
                    'success': True,
                    'data': {
                        'barcodes': results,
                        'validation': validation,
                        'product_info': product_info
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'ไม่พบบาร์โค้ดในรูปภาพ'
                })
        finally:
            # ลบไฟล์ชั่วคราว
            os.unlink(temp_path)
            
    except Exception as e:
        logger.error(f"Error scanning barcode from file: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการสแกนบาร์โค้ด'
        }), 500

@barcode_bp.route('/validate', methods=['POST'])
def validate_barcode():
    """ตรวจสอบความถูกต้องของบาร์โค้ด"""
    try:
        data = request.get_json()
        barcode_data = data.get('barcode')
        barcode_type = data.get('type')
        
        if not barcode_data:
            return jsonify({
                'success': False,
                'message': 'ไม่พบข้อมูลบาร์โค้ด'
            }), 400
        
        validation = scanner.validate_barcode(barcode_data, barcode_type)
        
        return jsonify({
            'success': True,
            'data': validation
        })
        
    except Exception as e:
        logger.error(f"Error validating barcode: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการตรวจสอบบาร์โค้ด'
        }), 500

@barcode_bp.route('/product-info/<barcode>', methods=['GET'])
def get_product_info(barcode):
    """ดึงข้อมูลสินค้าจากบาร์โค้ด"""
    try:
        product_info = scanner.get_product_info(barcode)
        
        if product_info:
            return jsonify({
                'success': True,
                'data': product_info
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ไม่พบข้อมูลสินค้า'
            })
            
    except Exception as e:
        logger.error(f"Error getting product info: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการดึงข้อมูลสินค้า'
        }), 500

@barcode_bp.route('/start-camera-scan', methods=['POST'])
def start_camera_scan():
    """เริ่มสแกนบาร์โค้ดจากกล้อง"""
    try:
        data = request.get_json()
        camera_index = data.get('camera_index', 0)
        timeout = data.get('timeout', 30)
        
        # สแกนจากกล้อง
        barcode_data = scanner.scan_from_camera(camera_index, timeout)
        
        if barcode_data:
            # ตรวจสอบความถูกต้อง
            validation = scanner.validate_barcode(barcode_data)
            
            # ดึงข้อมูลสินค้า
            product_info = scanner.get_product_info(barcode_data)
            
            return jsonify({
                'success': True,
                'data': {
                    'barcode': barcode_data,
                    'validation': validation,
                    'product_info': product_info
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ไม่พบบาร์โค้ดหรือหมดเวลา'
            })
            
    except Exception as e:
        logger.error(f"Error scanning from camera: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการสแกนจากกล้อง'
        }), 500


