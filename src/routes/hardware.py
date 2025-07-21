from flask import Blueprint, request, jsonify
import logging
from hardware_manager import HardwareManager

hardware_bp = Blueprint('hardware', __name__)
logger = logging.getLogger(__name__)

# สร้าง instance ของ HardwareManager
hardware_manager = HardwareManager()

@hardware_bp.route('/printers', methods=['GET'])
def get_printers():
    """ดึงรายการเครื่องพิมพ์ที่เชื่อมต่อ"""
    try:
        printers = hardware_manager.detect_printers()
        return jsonify({
            'success': True,
            'data': printers
        })
    except Exception as e:
        logger.error(f"Error getting printers: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการดึงข้อมูลเครื่องพิมพ์'
        }), 500

@hardware_bp.route('/printers/<printer_name>/configure', methods=['POST'])
def configure_printer(printer_name):
    """ตั้งค่าเครื่องพิมพ์"""
    try:
        data = request.get_json()
        success = hardware_manager.configure_printer(printer_name, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'ตั้งค่าเครื่องพิมพ์ {printer_name} เรียบร้อยแล้ว'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถตั้งค่าเครื่องพิมพ์ได้'
            }), 500
            
    except Exception as e:
        logger.error(f"Error configuring printer: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการตั้งค่าเครื่องพิมพ์'
        }), 500

@hardware_bp.route('/printers/<printer_name>/test', methods=['POST'])
def test_printer(printer_name):
    """ทดสอบเครื่องพิมพ์"""
    try:
        result = hardware_manager.test_printer(printer_name)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"Error testing printer: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการทดสอบเครื่องพิมพ์'
        }), 500

@hardware_bp.route('/print-receipt', methods=['POST'])
def print_receipt():
    """พิมพ์ใบเสร็จ"""
    try:
        data = request.get_json()
        printer_name = data.get('printer_name', 'Virtual POS Printer')
        receipt_data = data.get('receipt_data', {})
        
        success = hardware_manager.print_receipt(printer_name, receipt_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'พิมพ์ใบเสร็จเรียบร้อยแล้ว'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถพิมพ์ใบเสร็จได้'
            }), 500
            
    except Exception as e:
        logger.error(f"Error printing receipt: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการพิมพ์ใบเสร็จ'
        }), 500

@hardware_bp.route('/cash-drawer/open', methods=['POST'])
def open_cash_drawer():
    """เปิดลิ้นชักเงิน"""
    try:
        data = request.get_json()
        printer_name = data.get('printer_name')
        
        success = hardware_manager.open_cash_drawer(printer_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'เปิดลิ้นชักเงินเรียบร้อยแล้ว'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถเปิดลิ้นชักเงินได้'
            }), 500
            
    except Exception as e:
        logger.error(f"Error opening cash drawer: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการเปิดลิ้นชักเงิน'
        }), 500

@hardware_bp.route('/status', methods=['GET'])
def get_hardware_status():
    """ดึงสถานะอุปกรณ์ทั้งหมด"""
    try:
        status = hardware_manager.get_device_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"Error getting hardware status: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการดึงสถานะอุปกรณ์'
        }), 500

