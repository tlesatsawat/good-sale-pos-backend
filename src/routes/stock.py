from flask import Blueprint, request, jsonify, session

from datetime import datetime

stock_bp = Blueprint('stock', __name__)

@stock_bp.route('/stores/<int:store_id>/stock-items', methods=['POST'])
def create_stock_item(store_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['product_name', 'quantity']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if product exists, create if not
        product = Product.query.filter_by(name=data['product_name']).first()
        if not product:
            product = Product(
                name=data['product_name'],
                unit=data.get('unit', 'ชิ้น'),
                barcode_number=data.get('barcode_number')
            )
            db.session.add(product)
            db.session.flush()
        
        # Check if stock item already exists for this store and product
        existing_stock = StockItem.query.filter_by(
            store_id=store_id,
            product_id=product.id
        ).first()
        
        if existing_stock:
            return jsonify({'error': 'Stock item already exists for this product'}), 400
        
        # Create stock item
        stock_item = StockItem(
            store_id=store_id,
            product_id=product.id,
            quantity=data['quantity'],
            low_stock_threshold=data.get('low_stock_threshold', 10)
        )
        
        db.session.add(stock_item)
        db.session.commit()
        
        return jsonify({
            'message': 'Stock item created successfully',
            'stock_item': stock_item.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@stock_bp.route('/stores/<int:store_id>/stock-items', methods=['GET'])
def get_stock_items(store_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        # Get query parameters
        low_stock_only = request.args.get('low_stock_only', 'false').lower() == 'true'
        
        query = StockItem.query.filter_by(store_id=store_id)
        
        if low_stock_only:
            query = query.filter(StockItem.quantity <= StockItem.low_stock_threshold)
        
        stock_items = query.all()
        
        return jsonify({
            'stock_items': [item.to_dict() for item in stock_items]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@stock_bp.route('/stores/<int:store_id>/stock-items/<int:stock_item_id>', methods=['PUT'])
def update_stock_item(store_id, stock_item_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        stock_item = StockItem.query.filter_by(
            id=stock_item_id,
            store_id=store_id
        ).first()
        
        if not stock_item:
            return jsonify({'error': 'Stock item not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        if data.get('quantity') is not None:
            stock_item.quantity = data['quantity']
        
        if data.get('low_stock_threshold') is not None:
            stock_item.low_stock_threshold = data['low_stock_threshold']
        
        stock_item.last_updated = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Stock item updated successfully',
            'stock_item': stock_item.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@stock_bp.route('/stores/<int:store_id>/stock-items/<int:stock_item_id>', methods=['DELETE'])
def delete_stock_item(store_id, stock_item_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        stock_item = StockItem.query.filter_by(
            id=stock_item_id,
            store_id=store_id
        ).first()
        
        if not stock_item:
            return jsonify({'error': 'Stock item not found'}), 404
        
        db.session.delete(stock_item)
        db.session.commit()
        
        return jsonify({
            'message': 'Stock item deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@stock_bp.route('/stores/<int:store_id>/stock-alerts', methods=['GET'])
def get_stock_alerts(store_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        # Get items with low stock
        low_stock_items = StockItem.query.filter(
            StockItem.store_id == store_id,
            StockItem.quantity <= StockItem.low_stock_threshold
        ).all()
        
        alerts = []
        for item in low_stock_items:
            alerts.append({
                'stock_item': item.to_dict(),
                'alert_type': 'low_stock',
                'message': f'{item.product.name} เหลือเพียง {item.quantity} {item.product.unit}',
                'severity': 'high' if item.quantity == 0 else 'medium'
            })
        
        return jsonify({
            'alerts': alerts,
            'alert_count': len(alerts)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@stock_bp.route('/stores/<int:store_id>/stock-items/<int:stock_item_id>/adjust', methods=['POST'])
def adjust_stock(store_id, stock_item_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        stock_item = StockItem.query.filter_by(
            id=stock_item_id,
            store_id=store_id
        ).first()
        
        if not stock_item:
            return jsonify({'error': 'Stock item not found'}), 404
        
        data = request.get_json()
        
        if not data.get('adjustment_type') or data.get('quantity') is None:
            return jsonify({'error': 'adjustment_type and quantity are required'}), 400
        
        adjustment_type = data['adjustment_type']  # 'add' or 'subtract'
        quantity = data['quantity']
        
        if adjustment_type not in ['add', 'subtract']:
            return jsonify({'error': 'adjustment_type must be "add" or "subtract"'}), 400
        
        if quantity <= 0:
            return jsonify({'error': 'quantity must be positive'}), 400
        
        old_quantity = stock_item.quantity
        
        if adjustment_type == 'add':
            stock_item.quantity += quantity
        else:  # subtract
            if stock_item.quantity < quantity:
                return jsonify({'error': 'Cannot subtract more than current stock'}), 400
            stock_item.quantity -= quantity
        
        stock_item.last_updated = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': f'Stock adjusted successfully ({adjustment_type} {quantity})',
            'stock_item': stock_item.to_dict(),
            'adjustment': {
                'type': adjustment_type,
                'quantity': quantity,
                'old_quantity': old_quantity,
                'new_quantity': stock_item.quantity
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@stock_bp.route('/stores/<int:store_id>/scan-barcode', methods=['POST'])
def scan_barcode(store_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        data = request.get_json()
        
        if not data.get('barcode'):
            return jsonify({'error': 'barcode is required'}), 400
        
        barcode = data['barcode']
        
        # Find product by barcode
        product = Product.query.filter_by(barcode_number=barcode).first()
        
        if not product:
            return jsonify({
                'error': 'Product not found',
                'barcode': barcode,
                'suggestion': 'Create new product with this barcode'
            }), 404
        
        # Find stock item for this store
        stock_item = StockItem.query.filter_by(
            store_id=store_id,
            product_id=product.id
        ).first()
        
        result = {
            'product': product.to_dict(),
            'barcode': barcode
        }
        
        if stock_item:
            result['stock_item'] = stock_item.to_dict()
            result['in_stock'] = stock_item.quantity > 0
        else:
            result['stock_item'] = None
            result['in_stock'] = False
            result['message'] = 'Product found but not in store inventory'
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@stock_bp.route('/products', methods=['POST'])
def create_product():
    try:
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'error': 'name is required'}), 400
        
        # Check if product with same name or barcode exists
        existing_product = Product.query.filter_by(name=data['name']).first()
        if existing_product:
            return jsonify({'error': 'Product with this name already exists'}), 400
        
        if data.get('barcode_number'):
            existing_barcode = Product.query.filter_by(barcode_number=data['barcode_number']).first()
            if existing_barcode:
                return jsonify({'error': 'Product with this barcode already exists'}), 400
        
        product = Product(
            name=data['name'],
            unit=data.get('unit', 'ชิ้น'),
            barcode_number=data.get('barcode_number')
        )
        
        db.session.add(product)
        db.session.commit()
        
        return jsonify({
            'message': 'Product created successfully',
            'product': product.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@stock_bp.route('/products', methods=['GET'])
def get_products():
    try:
        search = request.args.get('search', '')
        
        query = Product.query
        if search:
            query = query.filter(Product.name.contains(search))
        
        products = query.all()
        
        return jsonify({
            'products': [product.to_dict() for product in products]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

