from flask import Blueprint, request, jsonify
import sqlite3
import logging
from datetime import datetime, timedelta
from cache import cached, invalidate_cache

stock_mgmt_bp = Blueprint('stock_management', __name__)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect('pos_database.db')
    conn.row_factory = sqlite3.Row
    return conn

@stock_mgmt_bp.route('/stock/items', methods=['GET'])
@cached(cache_name='menu', ttl=300)
def get_stock_items():
    """Get all stock items with current levels"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT si.*, 
                   COALESCE(SUM(sm.quantity_change), 0) as current_stock,
                   si.min_stock_level,
                   CASE 
                       WHEN COALESCE(SUM(sm.quantity_change), 0) <= si.min_stock_level 
                       THEN 'low' 
                       ELSE 'normal' 
                   END as stock_status
            FROM stock_items si
            LEFT JOIN stock_movements sm ON si.id = sm.stock_item_id
            GROUP BY si.id
            ORDER BY si.name
        ''')
        
        items = []
        for row in cursor.fetchall():
            items.append({
                'id': row['id'],
                'name': row['name'],
                'barcode': row['barcode'],
                'category': row['category'],
                'unit': row['unit'],
                'cost_price': row['cost_price'],
                'selling_price': row['selling_price'],
                'current_stock': row['current_stock'],
                'min_stock_level': row['min_stock_level'],
                'max_stock_level': row['max_stock_level'],
                'stock_status': row['stock_status'],
                'created_at': row['created_at']
            })
        
        conn.close()
        return jsonify(items)
        
    except Exception as e:
        logger.error(f"Error getting stock items: {str(e)}")
        return jsonify({'error': 'Failed to get stock items'}), 500

@stock_mgmt_bp.route('/stock/items', methods=['POST'])
def create_stock_item():
    """Create new stock item"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'barcode', 'category', 'unit', 'cost_price', 'selling_price']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO stock_items (
                name, barcode, category, unit, cost_price, selling_price,
                min_stock_level, max_stock_level, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['name'],
            data['barcode'],
            data['category'],
            data['unit'],
            data['cost_price'],
            data['selling_price'],
            data.get('min_stock_level', 10),
            data.get('max_stock_level', 100),
            datetime.now().isoformat()
        ))
        
        item_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Invalidate cache
        invalidate_cache('menu')
        
        logger.info(f"Stock item created: {data['name']} (ID: {item_id})")
        return jsonify({'id': item_id, 'message': 'Stock item created successfully'}), 201
        
    except Exception as e:
        logger.error(f"Error creating stock item: {str(e)}")
        return jsonify({'error': 'Failed to create stock item'}), 500

@stock_mgmt_bp.route('/stock/movements', methods=['POST'])
def record_stock_movement():
    """Record stock movement (in/out)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['stock_item_id', 'movement_type', 'quantity', 'reason']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate movement type
        if data['movement_type'] not in ['in', 'out', 'adjustment']:
            return jsonify({'error': 'Invalid movement type'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculate quantity change based on movement type
        quantity_change = data['quantity']
        if data['movement_type'] == 'out':
            quantity_change = -quantity_change
        
        cursor.execute('''
            INSERT INTO stock_movements (
                stock_item_id, movement_type, quantity_change, reason,
                reference_id, lot_number, expiry_date, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['stock_item_id'],
            data['movement_type'],
            quantity_change,
            data['reason'],
            data.get('reference_id'),
            data.get('lot_number'),
            data.get('expiry_date'),
            datetime.now().isoformat()
        ))
        
        movement_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Invalidate cache
        invalidate_cache('menu')
        
        logger.info(f"Stock movement recorded: {data['movement_type']} {data['quantity']} for item {data['stock_item_id']}")
        return jsonify({'id': movement_id, 'message': 'Stock movement recorded successfully'}), 201
        
    except Exception as e:
        logger.error(f"Error recording stock movement: {str(e)}")
        return jsonify({'error': 'Failed to record stock movement'}), 500

@stock_mgmt_bp.route('/stock/alerts', methods=['GET'])
@cached(cache_name='reports', ttl=60)
def get_stock_alerts():
    """Get stock alerts (low stock, expiring items)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Low stock alerts
        cursor.execute('''
            SELECT si.id, si.name, si.min_stock_level,
                   COALESCE(SUM(sm.quantity_change), 0) as current_stock
            FROM stock_items si
            LEFT JOIN stock_movements sm ON si.id = sm.stock_item_id
            GROUP BY si.id
            HAVING current_stock <= si.min_stock_level
            ORDER BY current_stock ASC
        ''')
        
        low_stock_items = []
        for row in cursor.fetchall():
            low_stock_items.append({
                'id': row['id'],
                'name': row['name'],
                'current_stock': row['current_stock'],
                'min_stock_level': row['min_stock_level'],
                'alert_type': 'low_stock'
            })
        
        # Expiring items (within 7 days)
        expiry_date = (datetime.now() + timedelta(days=7)).isoformat()
        cursor.execute('''
            SELECT si.name, sm.lot_number, sm.expiry_date,
                   SUM(sm.quantity_change) as quantity
            FROM stock_items si
            JOIN stock_movements sm ON si.id = sm.stock_item_id
            WHERE sm.expiry_date IS NOT NULL 
            AND sm.expiry_date <= ?
            AND sm.quantity_change > 0
            GROUP BY si.id, sm.lot_number, sm.expiry_date
            HAVING quantity > 0
            ORDER BY sm.expiry_date ASC
        ''', (expiry_date,))
        
        expiring_items = []
        for row in cursor.fetchall():
            expiring_items.append({
                'name': row['name'],
                'lot_number': row['lot_number'],
                'expiry_date': row['expiry_date'],
                'quantity': row['quantity'],
                'alert_type': 'expiring'
            })
        
        conn.close()
        
        alerts = {
            'low_stock': low_stock_items,
            'expiring': expiring_items,
            'total_alerts': len(low_stock_items) + len(expiring_items)
        }
        
        return jsonify(alerts)
        
    except Exception as e:
        logger.error(f"Error getting stock alerts: {str(e)}")
        return jsonify({'error': 'Failed to get stock alerts'}), 500

@stock_mgmt_bp.route('/stock/count', methods=['POST'])
def perform_stock_count():
    """Perform stock count and adjust inventory"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'items' not in data or not isinstance(data['items'], list):
            return jsonify({'error': 'Items list is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        adjustments = []
        
        for item in data['items']:
            if 'stock_item_id' not in item or 'counted_quantity' not in item:
                continue
            
            stock_item_id = item['stock_item_id']
            counted_quantity = item['counted_quantity']
            
            # Get current stock level
            cursor.execute('''
                SELECT COALESCE(SUM(quantity_change), 0) as current_stock
                FROM stock_movements
                WHERE stock_item_id = ?
            ''', (stock_item_id,))
            
            result = cursor.fetchone()
            current_stock = result['current_stock'] if result else 0
            
            # Calculate adjustment needed
            adjustment = counted_quantity - current_stock
            
            if adjustment != 0:
                # Record stock adjustment
                cursor.execute('''
                    INSERT INTO stock_movements (
                        stock_item_id, movement_type, quantity_change, reason,
                        reference_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    stock_item_id,
                    'adjustment',
                    adjustment,
                    f"Stock count adjustment: {current_stock} -> {counted_quantity}",
                    f"count_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    datetime.now().isoformat()
                ))
                
                adjustments.append({
                    'stock_item_id': stock_item_id,
                    'previous_stock': current_stock,
                    'counted_stock': counted_quantity,
                    'adjustment': adjustment
                })
        
        conn.commit()
        conn.close()
        
        # Invalidate cache
        invalidate_cache('menu')
        
        logger.info(f"Stock count completed with {len(adjustments)} adjustments")
        return jsonify({
            'message': 'Stock count completed successfully',
            'adjustments': adjustments,
            'total_adjustments': len(adjustments)
        }), 200
        
    except Exception as e:
        logger.error(f"Error performing stock count: {str(e)}")
        return jsonify({'error': 'Failed to perform stock count'}), 500

@stock_mgmt_bp.route('/stock/reports/movement', methods=['GET'])
@cached(cache_name='reports', ttl=300)
def get_stock_movement_report():
    """Get stock movement report"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        stock_item_id = request.args.get('stock_item_id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query
        query = '''
            SELECT sm.*, si.name as item_name, si.unit
            FROM stock_movements sm
            JOIN stock_items si ON sm.stock_item_id = si.id
            WHERE 1=1
        '''
        params = []
        
        if start_date:
            query += ' AND sm.created_at >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND sm.created_at <= ?'
            params.append(end_date)
        
        if stock_item_id:
            query += ' AND sm.stock_item_id = ?'
            params.append(stock_item_id)
        
        query += ' ORDER BY sm.created_at DESC LIMIT 1000'
        
        cursor.execute(query, params)
        
        movements = []
        for row in cursor.fetchall():
            movements.append({
                'id': row['id'],
                'stock_item_id': row['stock_item_id'],
                'item_name': row['item_name'],
                'unit': row['unit'],
                'movement_type': row['movement_type'],
                'quantity_change': row['quantity_change'],
                'reason': row['reason'],
                'reference_id': row['reference_id'],
                'lot_number': row['lot_number'],
                'expiry_date': row['expiry_date'],
                'created_at': row['created_at']
            })
        
        conn.close()
        return jsonify(movements)
        
    except Exception as e:
        logger.error(f"Error getting stock movement report: {str(e)}")
        return jsonify({'error': 'Failed to get stock movement report'}), 500

@stock_mgmt_bp.route('/stock/barcode/<barcode>', methods=['GET'])
@cached(cache_name='menu', ttl=300)
def get_item_by_barcode(barcode):
    """Get stock item by barcode"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT si.*, 
                   COALESCE(SUM(sm.quantity_change), 0) as current_stock
            FROM stock_items si
            LEFT JOIN stock_movements sm ON si.id = sm.stock_item_id
            WHERE si.barcode = ?
            GROUP BY si.id
        ''', (barcode,))
        
        row = cursor.fetchone()
        
        if not row:
            return jsonify({'error': 'Item not found'}), 404
        
        item = {
            'id': row['id'],
            'name': row['name'],
            'barcode': row['barcode'],
            'category': row['category'],
            'unit': row['unit'],
            'cost_price': row['cost_price'],
            'selling_price': row['selling_price'],
            'current_stock': row['current_stock'],
            'min_stock_level': row['min_stock_level'],
            'max_stock_level': row['max_stock_level']
        }
        
        conn.close()
        return jsonify(item)
        
    except Exception as e:
        logger.error(f"Error getting item by barcode: {str(e)}")
        return jsonify({'error': 'Failed to get item'}), 500

