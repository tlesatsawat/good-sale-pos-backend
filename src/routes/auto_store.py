from flask import Blueprint, request, jsonify
import logging
import json
from auto_store_manager import auto_store_manager

auto_store_bp = Blueprint('auto_store', __name__)
logger = logging.getLogger(__name__)

@auto_store_bp.route('/set-auto-close', methods=['POST'])
def set_auto_close():
    """ตั้งเวลาปิดร้านอัตโนมัติ"""
    try:
        data = request.get_json()
        store_id = data.get('store_id', 1)
        close_time = data.get('close_time')
        enabled = data.get('enabled', True)
        
        if not close_time:
            return jsonify({
                'success': False,
                'message': 'ไม่พบเวลาปิดร้าน'
            }), 400
        
        success = auto_store_manager.set_auto_close_time(store_id, close_time, enabled)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'ตั้งเวลาปิดร้านอัตโนมัติเรียบร้อยแล้ว ({close_time})'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถตั้งเวลาปิดร้านอัตโนมัติได้'
            }), 500
            
    except Exception as e:
        logger.error(f"Error setting auto close: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการตั้งเวลาปิดร้าน'
        }), 500

@auto_store_bp.route('/get-auto-close-settings/<int:store_id>', methods=['GET'])
def get_auto_close_settings(store_id):
    """ดึงการตั้งค่าปิดร้านอัตโนมัติ"""
    try:
        settings = auto_store_manager.get_auto_close_settings(store_id)
        
        return jsonify({
            'success': True,
            'data': settings
        })
        
    except Exception as e:
        logger.error(f"Error getting auto close settings: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการดึงการตั้งค่า'
        }), 500

@auto_store_bp.route('/generate-daily-summary', methods=['POST'])
def generate_daily_summary():
    """สร้างสรุปยอดขายรายวัน"""
    try:
        data = request.get_json()
        store_id = data.get('store_id', 1)
        target_date = data.get('date')  # YYYY-MM-DD format
        
        summary = auto_store_manager.generate_daily_summary(store_id, target_date)
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        logger.error(f"Error generating daily summary: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการสร้างสรุปยอดขาย'
        }), 500

@auto_store_bp.route('/generate-opening-summary', methods=['POST'])
def generate_opening_summary():
    """สร้างสรุปข้อมูลเมื่อเปิดร้าน"""
    try:
        data = request.get_json()
        store_id = data.get('store_id', 1)
        
        summary = auto_store_manager.generate_opening_summary(store_id)
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        logger.error(f"Error generating opening summary: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการสร้างสรุปเปิดร้าน'
        }), 500

@auto_store_bp.route('/start-scheduler', methods=['POST'])
def start_scheduler():
    """เริ่มต้น scheduler สำหรับปิดร้านอัตโนมัติ"""
    try:
        auto_store_manager.start_scheduler()
        
        return jsonify({
            'success': True,
            'message': 'เริ่มต้นระบบปิดร้านอัตโนมัติเรียบร้อยแล้ว'
        })
        
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการเริ่มต้นระบบ'
        }), 500

@auto_store_bp.route('/stop-scheduler', methods=['POST'])
def stop_scheduler():
    """หยุด scheduler"""
    try:
        auto_store_manager.stop_scheduler()
        
        return jsonify({
            'success': True,
            'message': 'หยุดระบบปิดร้านอัตโนมัติเรียบร้อยแล้ว'
        })
        
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการหยุดระบบ'
        }), 500

@auto_store_bp.route('/force-close-store', methods=['POST'])
def force_close_store():
    """บังคับปิดร้านและสร้างสรุปยอดขาย"""
    try:
        data = request.get_json()
        store_id = data.get('store_id', 1)
        
        # สร้างสรุปยอดขายก่อนปิดร้าน
        summary = auto_store_manager.generate_daily_summary(store_id)
        
        # ปิดร้าน (จำลอง)
        success = auto_store_manager._close_store(store_id, auto_close=False)
        
        if success:
            # บันทึกสรุปยอดขาย
            auto_store_manager._save_daily_summary(store_id, summary)
            
            return jsonify({
                'success': True,
                'data': summary,
                'message': 'ปิดร้านและสร้างสรุปยอดขายเรียบร้อยแล้ว'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถปิดร้านได้'
            }), 500
            
    except Exception as e:
        logger.error(f"Error force closing store: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการปิดร้าน'
        }), 500

@auto_store_bp.route('/scheduler-status', methods=['GET'])
def get_scheduler_status():
    """ดึงสถานะ scheduler"""
    try:
        return jsonify({
            'success': True,
            'data': {
                'scheduler_running': auto_store_manager.scheduler_running,
                'auto_close_settings': auto_store_manager.auto_close_settings
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการดึงสถานะระบบ'
        }), 500

