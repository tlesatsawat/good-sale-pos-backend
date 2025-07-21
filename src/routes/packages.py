from flask import Blueprint, request, jsonify, session
from database import get_packages_by_type, create_subscription

packages_bp = Blueprint('packages', __name__)

@packages_bp.route('/packages', methods=['GET'])
def get_packages():
    try:
        pos_type = request.args.get('pos_type')
        
        if not pos_type:
            return jsonify({'error': 'กรุณาระบุประเภทร้าน'}), 400
        
        packages = get_packages_by_type(pos_type)
        
        return jsonify({
            'packages': packages,
            'total': len(packages)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'เกิดข้อผิดพลาดในการโหลดแพ็กเกจ'}), 500

@packages_bp.route('/subscribe', methods=['POST'])
def subscribe():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'กรุณาเข้าสู่ระบบ'}), 401
        
        data = request.get_json()
        package_id = data.get('package_id')
        
        if not package_id:
            return jsonify({'error': 'กรุณาเลือกแพ็กเกจ'}), 400
        
        subscription = create_subscription(session['user_id'], package_id)
        
        return jsonify({
            'message': 'สมัครแพ็กเกจสำเร็จ',
            'subscription': subscription
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'เกิดข้อผิดพลาดในการสมัครแพ็กเกจ'}), 500

@packages_bp.route('/subscription/current', methods=['GET'])
def get_current_subscription():
    if 'user_id' not in session:
        return jsonify({'error': 'กรุณาเข้าสู่ระบบ'}), 401
    
    # TODO: Implement get current subscription from database
    return jsonify({
        'subscription': {
            'id': 1,
            'package': {
                'name': 'Pro Coffee',
                'description': 'แพ็กเกจมืออาชีพสำหรับร้านกาแฟ'
            },
            'start_date': '2025-07-12',
            'end_date': '2025-08-12',
            'status': 'active'
        }
    }), 200

@packages_bp.route('/features', methods=['GET'])
def get_features():
    # Return available features
    features = [
        {'id': 1, 'name': 'POS พื้นฐาน', 'description': 'ระบบขายหน้าร้านพื้นฐาน'},
        {'id': 2, 'name': 'รายงานยอดขาย', 'description': 'รายงานยอดขายรายวัน'},
        {'id': 3, 'name': 'จัดการเมนู', 'description': 'เพิ่ม ลบ แก้ไขเมนู'},
        {'id': 4, 'name': 'จอครัว', 'description': 'จอแสดงออเดอร์สำหรับครัว'},
        {'id': 5, 'name': 'AI วิเคราะห์', 'description': 'วิเคราะห์ยอดขายด้วย AI'},
        {'id': 6, 'name': 'หลายสาขา', 'description': 'จัดการหลายสาขา'},
        {'id': 7, 'name': 'การสนับสนุน 24/7', 'description': 'การสนับสนุนตลอด 24 ชั่วโมง'},
    ]
    
    return jsonify({'features': features}), 200

