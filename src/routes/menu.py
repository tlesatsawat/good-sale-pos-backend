from flask import Blueprint, request, jsonify, session

from datetime import datetime

menu_bp = Blueprint('menu', __name__)

@menu_bp.route('/stores/<int:store_id>/menu-items', methods=['POST'])
def create_menu_item(store_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'price']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        menu_item = MenuItem(
            store_id=store_id,
            name=data['name'],
            description=data.get('description', ''),
            price=data['price'],
            category=data.get('category', ''),
            image_url=data.get('image_url', ''),
            is_custom_order=data.get('is_custom_order', False)
        )
        
        db.session.add(menu_item)
        db.session.flush()  # Get the ID before commit
        
        # Add toppings if provided
        if data.get('toppings'):
            for topping_data in data['toppings']:
                topping = Topping(
                    menu_item_id=menu_item.id,
                    name=topping_data['name'],
                    price=topping_data.get('price', 0)
                )
                db.session.add(topping)
        
        # Add sizes if provided (for coffee shop)
        if data.get('sizes'):
            for size_data in data['sizes']:
                size = Size(
                    menu_item_id=menu_item.id,
                    name=size_data['name'],
                    price=size_data.get('price', 0)
                )
                db.session.add(size)
        
        # Add sweetness levels if provided (for coffee shop)
        if data.get('sweetness_levels'):
            for sweetness_data in data['sweetness_levels']:
                sweetness = Sweetness(
                    menu_item_id=menu_item.id,
                    level=sweetness_data['level'],
                    price=sweetness_data.get('price', 0)
                )
                db.session.add(sweetness)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Menu item created successfully',
            'menu_item': menu_item.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@menu_bp.route('/stores/<int:store_id>/menu-items', methods=['GET'])
def get_menu_items(store_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        category = request.args.get('category')
        
        query = MenuItem.query.filter_by(store_id=store_id)
        if category:
            query = query.filter_by(category=category)
        
        menu_items = query.all()
        
        return jsonify({
            'menu_items': [item.to_dict() for item in menu_items]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@menu_bp.route('/stores/<int:store_id>/menu-items/<int:menu_item_id>', methods=['GET'])
def get_menu_item(store_id, menu_item_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        menu_item = MenuItem.query.filter_by(id=menu_item_id, store_id=store_id).first()
        
        if not menu_item:
            return jsonify({'error': 'Menu item not found'}), 404
        
        return jsonify({
            'menu_item': menu_item.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@menu_bp.route('/stores/<int:store_id>/menu-items/<int:menu_item_id>', methods=['PUT'])
def update_menu_item(store_id, menu_item_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        menu_item = MenuItem.query.filter_by(id=menu_item_id, store_id=store_id).first()
        
        if not menu_item:
            return jsonify({'error': 'Menu item not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        if data.get('name'):
            menu_item.name = data['name']
        if data.get('description') is not None:
            menu_item.description = data['description']
        if data.get('price'):
            menu_item.price = data['price']
        if data.get('category') is not None:
            menu_item.category = data['category']
        if data.get('image_url') is not None:
            menu_item.image_url = data['image_url']
        if data.get('is_custom_order') is not None:
            menu_item.is_custom_order = data['is_custom_order']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Menu item updated successfully',
            'menu_item': menu_item.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@menu_bp.route('/stores/<int:store_id>/menu-items/<int:menu_item_id>', methods=['DELETE'])
def delete_menu_item(store_id, menu_item_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        menu_item = MenuItem.query.filter_by(id=menu_item_id, store_id=store_id).first()
        
        if not menu_item:
            return jsonify({'error': 'Menu item not found'}), 404
        
        db.session.delete(menu_item)
        db.session.commit()
        
        return jsonify({
            'message': 'Menu item deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Topping management
@menu_bp.route('/stores/<int:store_id>/menu-items/<int:menu_item_id>/toppings', methods=['POST'])
def add_topping(store_id, menu_item_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        menu_item = MenuItem.query.filter_by(id=menu_item_id, store_id=store_id).first()
        
        if not menu_item:
            return jsonify({'error': 'Menu item not found'}), 404
        
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'error': 'name is required'}), 400
        
        topping = Topping(
            menu_item_id=menu_item_id,
            name=data['name'],
            price=data.get('price', 0)
        )
        
        db.session.add(topping)
        db.session.commit()
        
        return jsonify({
            'message': 'Topping added successfully',
            'topping': topping.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@menu_bp.route('/stores/<int:store_id>/menu-items/<int:menu_item_id>/toppings/<int:topping_id>', methods=['PUT'])
def update_topping(store_id, menu_item_id, topping_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        topping = Topping.query.filter_by(id=topping_id, menu_item_id=menu_item_id).first()
        
        if not topping:
            return jsonify({'error': 'Topping not found'}), 404
        
        data = request.get_json()
        
        if data.get('name'):
            topping.name = data['name']
        if data.get('price') is not None:
            topping.price = data['price']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Topping updated successfully',
            'topping': topping.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@menu_bp.route('/stores/<int:store_id>/menu-items/<int:menu_item_id>/toppings/<int:topping_id>', methods=['DELETE'])
def delete_topping(store_id, menu_item_id, topping_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        topping = Topping.query.filter_by(id=topping_id, menu_item_id=menu_item_id).first()
        
        if not topping:
            return jsonify({'error': 'Topping not found'}), 404
        
        db.session.delete(topping)
        db.session.commit()
        
        return jsonify({
            'message': 'Topping deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Size management (for coffee shop)
@menu_bp.route('/stores/<int:store_id>/menu-items/<int:menu_item_id>/sizes', methods=['POST'])
def add_size(store_id, menu_item_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        menu_item = MenuItem.query.filter_by(id=menu_item_id, store_id=store_id).first()
        
        if not menu_item:
            return jsonify({'error': 'Menu item not found'}), 404
        
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'error': 'name is required'}), 400
        
        size = Size(
            menu_item_id=menu_item_id,
            name=data['name'],
            price=data.get('price', 0)
        )
        
        db.session.add(size)
        db.session.commit()
        
        return jsonify({
            'message': 'Size added successfully',
            'size': size.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Sweetness management (for coffee shop)
@menu_bp.route('/stores/<int:store_id>/menu-items/<int:menu_item_id>/sweetness', methods=['POST'])
def add_sweetness(store_id, menu_item_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        menu_item = MenuItem.query.filter_by(id=menu_item_id, store_id=store_id).first()
        
        if not menu_item:
            return jsonify({'error': 'Menu item not found'}), 404
        
        data = request.get_json()
        
        if not data.get('level'):
            return jsonify({'error': 'level is required'}), 400
        
        sweetness = Sweetness(
            menu_item_id=menu_item_id,
            level=data['level'],
            price=data.get('price', 0)
        )
        
        db.session.add(sweetness)
        db.session.commit()
        
        return jsonify({
            'message': 'Sweetness level added successfully',
            'sweetness': sweetness.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

