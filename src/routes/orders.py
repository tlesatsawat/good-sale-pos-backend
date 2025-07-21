from flask import Blueprint, request, jsonify
import sqlite3
import logging
from datetime import datetime, date

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/stores/<int:store_id>/orders', methods=['POST'])
def create_order(store_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['payment_method', 'order_items']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate payment method
        valid_payment_methods = ['cash', 'qr_code']
        if data['payment_method'] not in valid_payment_methods:
            return jsonify({'error': 'Invalid payment method'}), 400
        
        # Calculate total amount
        total_amount = 0
        order_items_data = data['order_items']
        
        for item_data in order_items_data:
            if not item_data.get('item_name') or not item_data.get('price') or not item_data.get('quantity'):
                return jsonify({'error': 'Each order item must have item_name, price, and quantity'}), 400
            
            item_total = float(item_data['price']) * int(item_data['quantity'])
            total_amount += item_total
        
        # Create order
        order = Order(
            store_id=store_id,
            total_amount=total_amount,
            payment_method=data['payment_method'],
            status='new',
            notes=data.get('notes', '')
        )
        
        db.session.add(order)
        db.session.flush()  # Get the ID before commit
        
        # Create order items
        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=item_data.get('menu_item_id'),
                item_name=item_data['item_name'],
                price=item_data['price'],
                quantity=item_data['quantity'],
                notes=item_data.get('notes', '')
            )
            db.session.add(order_item)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Order created successfully',
            'order': order.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@orders_bp.route('/stores/<int:store_id>/orders', methods=['GET'])
def get_orders(store_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        # Get query parameters
        status = request.args.get('status')
        date_filter = request.args.get('date')  # YYYY-MM-DD format
        limit = request.args.get('limit', 50, type=int)
        
        query = Order.query.filter_by(store_id=store_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                query = query.filter(func.date(Order.order_time) == filter_date)
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        orders = query.order_by(desc(Order.order_time)).limit(limit).all()
        
        return jsonify({
            'orders': [order.to_dict() for order in orders]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@orders_bp.route('/stores/<int:store_id>/orders/<int:order_id>', methods=['GET'])
def get_order(store_id, order_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        order = Order.query.filter_by(id=order_id, store_id=store_id).first()
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        return jsonify({
            'order': order.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@orders_bp.route('/stores/<int:store_id>/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(store_id, order_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        order = Order.query.filter_by(id=order_id, store_id=store_id).first()
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        data = request.get_json()
        
        if not data.get('status'):
            return jsonify({'error': 'status is required'}), 400
        
        # Validate status
        valid_statuses = ['new', 'preparing', 'ready', 'completed']
        if data['status'] not in valid_statuses:
            return jsonify({'error': 'Invalid status'}), 400
        
        order.status = data['status']
        db.session.commit()
        
        return jsonify({
            'message': 'Order status updated successfully',
            'order': order.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@orders_bp.route('/stores/<int:store_id>/orders/<int:order_id>/payment', methods=['POST'])
def record_payment(store_id, order_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        order = Order.query.filter_by(id=order_id, store_id=store_id).first()
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        data = request.get_json()
        
        # Update payment method if provided
        if data.get('payment_method'):
            valid_payment_methods = ['cash', 'qr_code']
            if data['payment_method'] not in valid_payment_methods:
                return jsonify({'error': 'Invalid payment method'}), 400
            order.payment_method = data['payment_method']
        
        # Mark order as completed
        order.status = 'completed'
        db.session.commit()
        
        return jsonify({
            'message': 'Payment recorded successfully',
            'order': order.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@orders_bp.route('/stores/<int:store_id>/orders/<int:order_id>/qr-slip', methods=['POST'])
def upload_qr_slip(store_id, order_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        order = Order.query.filter_by(id=order_id, store_id=store_id).first()
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        data = request.get_json()
        
        if not data.get('slip_url'):
            return jsonify({'error': 'slip_url is required'}), 400
        
        order.qr_code_slip_url = data['slip_url']
        order.payment_method = 'qr_code'
        order.status = 'completed'
        db.session.commit()
        
        # In a real application, you would send this to LINE API
        line_message = f"ได้รับการชำระเงินผ่าน QR Code\\nออร์เดอร์: #{order.id}\\nจำนวนเงิน: {order.total_amount} บาท\\nร้าน: {store.name}"
        
        return jsonify({
            'message': 'QR slip uploaded successfully',
            'order': order.to_dict(),
            'line_message_sent': line_message
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@orders_bp.route('/stores/<int:store_id>/kitchen-orders', methods=['GET'])
def get_kitchen_orders(store_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        # Get orders that are not completed (for kitchen display)
        orders = Order.query.filter(
            Order.store_id == store_id,
            Order.status.in_(['new', 'preparing', 'ready'])
        ).order_by(Order.order_time).all()
        
        return jsonify({
            'kitchen_orders': [order.to_dict() for order in orders]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@orders_bp.route('/stores/<int:store_id>/custom-order', methods=['POST'])
def create_custom_order(store_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        data = request.get_json()
        
        # Validate required fields for custom order
        required_fields = ['item_name', 'price', 'payment_method']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Create order with custom item
        order = Order(
            store_id=store_id,
            total_amount=data['price'],
            payment_method=data['payment_method'],
            status='new',
            notes=data.get('notes', '')
        )
        
        db.session.add(order)
        db.session.flush()
        
        # Create custom order item
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=None,  # No menu item for custom orders
            item_name=data['item_name'],
            price=data['price'],
            quantity=data.get('quantity', 1),
            notes=data.get('notes', '')
        )
        
        db.session.add(order_item)
        db.session.commit()
        
        return jsonify({
            'message': 'Custom order created successfully',
            'order': order.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

