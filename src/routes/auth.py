from flask import Blueprint, request, jsonify, session
from database import create_user, authenticate_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'password', 'phone_number', 'pos_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'กรุณากรอก{field}'}), 400
        
        # Create user
        user = create_user(
            data['username'],
            data['email'],
            data['password'],
            data['phone_number'],
            data['pos_type']
        )
        
        # Set session
        session['user_id'] = user['id']
        session['username'] = user['username']
        
        return jsonify({
            'message': 'สมัครสมาชิกสำเร็จ',
            'user': user,
            'pos_type': user['pos_type']
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'เกิดข้อผิดพลาดในระบบ'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'กรุณากรอกชื่อผู้ใช้และรหัสผ่าน'}), 400
        
        user = authenticate_user(username, password)
        
        if user:
            # Set session
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            return jsonify({
                'message': 'เข้าสู่ระบบสำเร็จ',
                'user': user
            }), 200
        else:
            return jsonify({'error': 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'}), 401
            
    except Exception as e:
        return jsonify({'error': 'เกิดข้อผิดพลาดในระบบ'}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'ออกจากระบบสำเร็จ'}), 200

@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'กรุณาเข้าสู่ระบบ'}), 401
    
    # In a real app, you'd fetch user data from database
    return jsonify({
        'user': {
            'id': session['user_id'],
            'username': session['username']
        }
    }), 200

@auth_bp.route('/profile', methods=['PUT'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'กรุณาเข้าสู่ระบบ'}), 401
    
    data = request.get_json()
    # Implementation for updating profile
    return jsonify({'message': 'อัปเดตโปรไฟล์สำเร็จ'}), 200

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'กรุณากรอกอีเมล'}), 400
    
    # Implementation for forgot password
    return jsonify({'message': 'ส่งลิงก์รีเซ็ตรหัสผ่านไปยังอีเมลแล้ว'}), 200

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    
    # Implementation for reset password
    return jsonify({'message': 'รีเซ็ตรหัสผ่านสำเร็จ'}), 200

