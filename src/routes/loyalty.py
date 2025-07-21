from flask import Blueprint, request, jsonify
import sqlite3
import logging
from datetime import datetime, timedelta
from cache import cached, invalidate_cache
import uuid

loyalty_bp = Blueprint('loyalty', __name__)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect('pos_database.db')
    conn.row_factory = sqlite3.Row
    return conn

@loyalty_bp.route('/loyalty/members', methods=['POST'])
def register_member():
    """Register new loyalty member"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'phone', 'email']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if member already exists
        cursor.execute('SELECT id FROM loyalty_members WHERE phone = ? OR email = ?', 
                      (data['phone'], data['email']))
        if cursor.fetchone():
            return jsonify({'error': 'Member already exists with this phone or email'}), 400
        
        # Generate member ID
        member_id = str(uuid.uuid4())[:8].upper()
        
        cursor.execute('''
            INSERT INTO loyalty_members (
                member_id, name, phone, email, date_of_birth, 
                points_balance, tier, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            member_id,
            data['name'],
            data['phone'],
            data['email'],
            data.get('date_of_birth'),
            0,  # Initial points
            'Bronze',  # Initial tier
            datetime.now().isoformat()
        ))
        
        member_db_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"New loyalty member registered: {data['name']} (ID: {member_id})")
        return jsonify({
            'id': member_db_id,
            'member_id': member_id,
            'message': 'Member registered successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Error registering member: {str(e)}")
        return jsonify({'error': 'Failed to register member'}), 500

@loyalty_bp.route('/loyalty/members/<member_id>', methods=['GET'])
@cached(cache_name='orders', ttl=60)
def get_member_profile(member_id):
    """Get member profile and points balance"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT lm.*, 
                   COUNT(pt.id) as total_transactions,
                   COALESCE(SUM(CASE WHEN pt.transaction_type = 'earn' THEN pt.points ELSE 0 END), 0) as total_earned,
                   COALESCE(SUM(CASE WHEN pt.transaction_type = 'redeem' THEN pt.points ELSE 0 END), 0) as total_redeemed
            FROM loyalty_members lm
            LEFT JOIN points_transactions pt ON lm.id = pt.member_id
            WHERE lm.member_id = ?
            GROUP BY lm.id
        ''', (member_id,))
        
        row = cursor.fetchone()
        
        if not row:
            return jsonify({'error': 'Member not found'}), 404
        
        # Get recent transactions
        cursor.execute('''
            SELECT * FROM points_transactions
            WHERE member_id = ?
            ORDER BY created_at DESC
            LIMIT 10
        ''', (row['id'],))
        
        transactions = []
        for trans_row in cursor.fetchall():
            transactions.append({
                'id': trans_row['id'],
                'transaction_type': trans_row['transaction_type'],
                'points': trans_row['points'],
                'description': trans_row['description'],
                'order_id': trans_row['order_id'],
                'created_at': trans_row['created_at']
            })
        
        member_profile = {
            'id': row['id'],
            'member_id': row['member_id'],
            'name': row['name'],
            'phone': row['phone'],
            'email': row['email'],
            'date_of_birth': row['date_of_birth'],
            'points_balance': row['points_balance'],
            'tier': row['tier'],
            'total_transactions': row['total_transactions'],
            'total_earned': row['total_earned'],
            'total_redeemed': row['total_redeemed'],
            'recent_transactions': transactions,
            'created_at': row['created_at']
        }
        
        conn.close()
        return jsonify(member_profile)
        
    except Exception as e:
        logger.error(f"Error getting member profile: {str(e)}")
        return jsonify({'error': 'Failed to get member profile'}), 500

@loyalty_bp.route('/loyalty/earn', methods=['POST'])
def earn_points():
    """Earn points from purchase"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['member_id', 'order_id', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get member
        cursor.execute('SELECT * FROM loyalty_members WHERE member_id = ?', (data['member_id'],))
        member = cursor.fetchone()
        
        if not member:
            return jsonify({'error': 'Member not found'}), 404
        
        # Calculate points (1 point per 10 baht spent)
        points_earned = int(data['amount'] / 10)
        
        if points_earned <= 0:
            return jsonify({'error': 'Amount too small to earn points'}), 400
        
        # Add points transaction
        cursor.execute('''
            INSERT INTO points_transactions (
                member_id, transaction_type, points, description, order_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            member['id'],
            'earn',
            points_earned,
            f"Earned from purchase (฿{data['amount']})",
            data['order_id'],
            datetime.now().isoformat()
        ))
        
        # Update member points balance
        new_balance = member['points_balance'] + points_earned
        cursor.execute('''
            UPDATE loyalty_members 
            SET points_balance = ?, updated_at = ?
            WHERE id = ?
        ''', (new_balance, datetime.now().isoformat(), member['id']))
        
        # Check for tier upgrade
        new_tier = calculate_tier(new_balance)
        if new_tier != member['tier']:
            cursor.execute('''
                UPDATE loyalty_members 
                SET tier = ?
                WHERE id = ?
            ''', (new_tier, member['id']))
        
        conn.commit()
        conn.close()
        
        # Invalidate cache
        invalidate_cache('orders')
        
        logger.info(f"Points earned: {points_earned} for member {data['member_id']}")
        return jsonify({
            'points_earned': points_earned,
            'new_balance': new_balance,
            'tier': new_tier,
            'message': 'Points earned successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error earning points: {str(e)}")
        return jsonify({'error': 'Failed to earn points'}), 500

@loyalty_bp.route('/loyalty/redeem', methods=['POST'])
def redeem_points():
    """Redeem points for rewards"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['member_id', 'points_to_redeem', 'reward_description']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get member
        cursor.execute('SELECT * FROM loyalty_members WHERE member_id = ?', (data['member_id'],))
        member = cursor.fetchone()
        
        if not member:
            return jsonify({'error': 'Member not found'}), 404
        
        points_to_redeem = data['points_to_redeem']
        
        # Check if member has enough points
        if member['points_balance'] < points_to_redeem:
            return jsonify({'error': 'Insufficient points balance'}), 400
        
        # Add redemption transaction
        cursor.execute('''
            INSERT INTO points_transactions (
                member_id, transaction_type, points, description, order_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            member['id'],
            'redeem',
            -points_to_redeem,  # Negative for redemption
            data['reward_description'],
            data.get('order_id'),
            datetime.now().isoformat()
        ))
        
        # Update member points balance
        new_balance = member['points_balance'] - points_to_redeem
        cursor.execute('''
            UPDATE loyalty_members 
            SET points_balance = ?, updated_at = ?
            WHERE id = ?
        ''', (new_balance, datetime.now().isoformat(), member['id']))
        
        conn.commit()
        conn.close()
        
        # Invalidate cache
        invalidate_cache('orders')
        
        logger.info(f"Points redeemed: {points_to_redeem} for member {data['member_id']}")
        return jsonify({
            'points_redeemed': points_to_redeem,
            'new_balance': new_balance,
            'message': 'Points redeemed successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error redeeming points: {str(e)}")
        return jsonify({'error': 'Failed to redeem points'}), 500

@loyalty_bp.route('/loyalty/rewards', methods=['GET'])
@cached(cache_name='packages', ttl=3600)
def get_available_rewards():
    """Get available rewards for redemption"""
    try:
        # Predefined rewards catalog
        rewards = [
            {
                'id': 1,
                'name': 'ส่วนลด 10 บาท',
                'description': 'รับส่วนลด 10 บาท สำหรับการซื้อครั้งถัดไป',
                'points_required': 100,
                'category': 'discount',
                'terms': 'ใช้ได้กับการซื้อขั้นต่ำ 50 บาท'
            },
            {
                'id': 2,
                'name': 'ส่วนลด 25 บาท',
                'description': 'รับส่วนลด 25 บาท สำหรับการซื้อครั้งถัดไป',
                'points_required': 250,
                'category': 'discount',
                'terms': 'ใช้ได้กับการซื้อขั้นต่ำ 100 บาท'
            },
            {
                'id': 3,
                'name': 'เครื่องดื่มฟรี',
                'description': 'รับเครื่องดื่มฟรี 1 แก้ว (เมนูราคาไม่เกิน 50 บาท)',
                'points_required': 300,
                'category': 'free_item',
                'terms': 'เลือกได้จากเมนูที่กำหนด'
            },
            {
                'id': 4,
                'name': 'ส่วนลด 50 บาท',
                'description': 'รับส่วนลด 50 บาท สำหรับการซื้อครั้งถัดไป',
                'points_required': 500,
                'category': 'discount',
                'terms': 'ใช้ได้กับการซื้อขั้นต่ำ 200 บาท'
            },
            {
                'id': 5,
                'name': 'ส่วนลด 100 บาท',
                'description': 'รับส่วนลด 100 บาท สำหรับการซื้อครั้งถัดไป',
                'points_required': 1000,
                'category': 'discount',
                'terms': 'ใช้ได้กับการซื้อขั้นต่ำ 500 บาท'
            }
        ]
        
        return jsonify(rewards)
        
    except Exception as e:
        logger.error(f"Error getting rewards: {str(e)}")
        return jsonify({'error': 'Failed to get rewards'}), 500

@loyalty_bp.route('/loyalty/tiers', methods=['GET'])
@cached(cache_name='packages', ttl=3600)
def get_tier_info():
    """Get loyalty tier information"""
    try:
        tiers = [
            {
                'name': 'Bronze',
                'min_points': 0,
                'max_points': 999,
                'benefits': [
                    'สะสมแต้ม 1 แต้ม ต่อการใช้จ่าย 10 บาท',
                    'รับข่าวสารโปรโมชั่นพิเศษ'
                ],
                'color': '#CD7F32'
            },
            {
                'name': 'Silver',
                'min_points': 1000,
                'max_points': 4999,
                'benefits': [
                    'สะสมแต้ม 1.2 แต้ม ต่อการใช้จ่าย 10 บาท',
                    'ส่วนลดพิเศษในวันเกิด 10%',
                    'รับข่าวสารโปรโมชั่นพิเศษ'
                ],
                'color': '#C0C0C0'
            },
            {
                'name': 'Gold',
                'min_points': 5000,
                'max_points': 9999,
                'benefits': [
                    'สะสมแต้ม 1.5 แต้ม ต่อการใช้จ่าย 10 บาท',
                    'ส่วนลดพิเศษในวันเกิด 15%',
                    'เครื่องดื่มฟรี 1 แก้วในวันเกิด',
                    'รับข่าวสารโปรโมชั่นพิเศษ'
                ],
                'color': '#FFD700'
            },
            {
                'name': 'Platinum',
                'min_points': 10000,
                'max_points': None,
                'benefits': [
                    'สะสมแต้ม 2 แต้ม ต่อการใช้จ่าย 10 บาท',
                    'ส่วนลดพิเศษในวันเกิด 20%',
                    'เครื่องดื่มฟรี 2 แก้วในวันเกิด',
                    'ข้ามคิวในช่วงเวลาเร่งด่วน',
                    'รับข่าวสารโปรโมชั่นพิเศษ'
                ],
                'color': '#E5E4E2'
            }
        ]
        
        return jsonify(tiers)
        
    except Exception as e:
        logger.error(f"Error getting tier info: {str(e)}")
        return jsonify({'error': 'Failed to get tier info'}), 500

def calculate_tier(points_balance):
    """Calculate member tier based on points balance"""
    if points_balance >= 10000:
        return 'Platinum'
    elif points_balance >= 5000:
        return 'Gold'
    elif points_balance >= 1000:
        return 'Silver'
    else:
        return 'Bronze'

@loyalty_bp.route('/loyalty/search', methods=['GET'])
def search_member():
    """Search member by phone or member ID"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT member_id, name, phone, points_balance, tier
            FROM loyalty_members
            WHERE phone LIKE ? OR member_id LIKE ? OR name LIKE ?
            LIMIT 10
        ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
        
        members = []
        for row in cursor.fetchall():
            members.append({
                'member_id': row['member_id'],
                'name': row['name'],
                'phone': row['phone'],
                'points_balance': row['points_balance'],
                'tier': row['tier']
            })
        
        conn.close()
        return jsonify(members)
        
    except Exception as e:
        logger.error(f"Error searching members: {str(e)}")
        return jsonify({'error': 'Failed to search members'}), 500

