import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Set
from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
import sqlite3

class RealTimeManager:
    def __init__(self, app: Flask = None):
        self.app = app
        self.socketio = None
        self.connected_clients: Dict[str, Set[str]] = {}  # room_id -> set of session_ids
        self.client_rooms: Dict[str, str] = {}  # session_id -> room_id
        self.logger = logging.getLogger(__name__)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize SocketIO with Flask app"""
        self.app = app
        self.socketio = SocketIO(
            app,
            cors_allowed_origins="*",
            async_mode='threading',
            logger=True,
            engineio_logger=True
        )
        
        # Register event handlers
        self._register_handlers()
        
        self.logger.info("Real-time WebSocket support initialized")
    
    def _register_handlers(self):
        """Register WebSocket event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            self.logger.info(f"Client connected: {request.sid}")
            emit('connected', {'message': 'Connected to GOOD SALE POS real-time service'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            session_id = request.sid
            self.logger.info(f"Client disconnected: {session_id}")
            
            # Remove from room if was in one
            if session_id in self.client_rooms:
                room_id = self.client_rooms[session_id]
                self._leave_room(session_id, room_id)
        
        @self.socketio.on('join_store')
        def handle_join_store(data):
            """Join a store room for real-time updates"""
            session_id = request.sid
            store_id = data.get('store_id')
            user_role = data.get('role', 'staff')  # staff, kitchen, customer
            
            if not store_id:
                emit('error', {'message': 'Store ID is required'})
                return
            
            room_id = f"store_{store_id}_{user_role}"
            
            # Leave previous room if any
            if session_id in self.client_rooms:
                old_room = self.client_rooms[session_id]
                self._leave_room(session_id, old_room)
            
            # Join new room
            join_room(room_id)
            self._join_room(session_id, room_id)
            
            self.logger.info(f"Client {session_id} joined room {room_id}")
            emit('joined_store', {
                'store_id': store_id,
                'role': user_role,
                'room_id': room_id
            })
        
        @self.socketio.on('leave_store')
        def handle_leave_store():
            """Leave current store room"""
            session_id = request.sid
            
            if session_id in self.client_rooms:
                room_id = self.client_rooms[session_id]
                leave_room(room_id)
                self._leave_room(session_id, room_id)
                
                self.logger.info(f"Client {session_id} left room {room_id}")
                emit('left_store', {'message': 'Left store room'})
        
        @self.socketio.on('ping')
        def handle_ping():
            """Handle ping for connection testing"""
            emit('pong', {'timestamp': datetime.now().isoformat()})
    
    def _join_room(self, session_id: str, room_id: str):
        """Add client to room tracking"""
        if room_id not in self.connected_clients:
            self.connected_clients[room_id] = set()
        
        self.connected_clients[room_id].add(session_id)
        self.client_rooms[session_id] = room_id
    
    def _leave_room(self, session_id: str, room_id: str):
        """Remove client from room tracking"""
        if room_id in self.connected_clients:
            self.connected_clients[room_id].discard(session_id)
            
            # Clean up empty rooms
            if not self.connected_clients[room_id]:
                del self.connected_clients[room_id]
        
        if session_id in self.client_rooms:
            del self.client_rooms[session_id]
    
    def broadcast_to_store(self, store_id: int, event: str, data: Dict, role: str = None):
        """Broadcast event to all clients in a store"""
        if not self.socketio:
            return
        
        if role:
            room_id = f"store_{store_id}_{role}"
            self.socketio.emit(event, data, room=room_id)
            self.logger.debug(f"Broadcasted {event} to {room_id}")
        else:
            # Broadcast to all roles in the store
            for role_type in ['staff', 'kitchen', 'customer']:
                room_id = f"store_{store_id}_{role_type}"
                if room_id in self.connected_clients:
                    self.socketio.emit(event, data, room=room_id)
            
            self.logger.debug(f"Broadcasted {event} to all roles in store {store_id}")
    
    def notify_new_order(self, store_id: int, order_data: Dict):
        """Notify about new order"""
        # Notify kitchen
        self.broadcast_to_store(store_id, 'new_order', {
            'order': order_data,
            'timestamp': datetime.now().isoformat()
        }, role='kitchen')
        
        # Notify staff
        self.broadcast_to_store(store_id, 'order_update', {
            'order': order_data,
            'action': 'created',
            'timestamp': datetime.now().isoformat()
        }, role='staff')
    
    def notify_order_status_change(self, store_id: int, order_id: int, old_status: str, new_status: str, order_data: Dict = None):
        """Notify about order status change"""
        notification_data = {
            'order_id': order_id,
            'old_status': old_status,
            'new_status': new_status,
            'timestamp': datetime.now().isoformat()
        }
        
        if order_data:
            notification_data['order'] = order_data
        
        # Notify all roles
        self.broadcast_to_store(store_id, 'order_status_changed', notification_data)
    
    def notify_menu_update(self, store_id: int, menu_item_data: Dict, action: str):
        """Notify about menu updates"""
        self.broadcast_to_store(store_id, 'menu_updated', {
            'menu_item': menu_item_data,
            'action': action,  # 'created', 'updated', 'deleted'
            'timestamp': datetime.now().isoformat()
        })
    
    def notify_stock_alert(self, store_id: int, stock_data: Dict, alert_type: str):
        """Notify about stock alerts"""
        self.broadcast_to_store(store_id, 'stock_alert', {
            'stock_item': stock_data,
            'alert_type': alert_type,  # 'low_stock', 'out_of_stock', 'expiring_soon'
            'timestamp': datetime.now().isoformat()
        }, role='staff')
    
    def notify_sales_update(self, store_id: int, sales_data: Dict):
        """Notify about sales updates for dashboard"""
        self.broadcast_to_store(store_id, 'sales_updated', {
            'sales': sales_data,
            'timestamp': datetime.now().isoformat()
        }, role='staff')
    
    def notify_customer_display(self, store_id: int, display_data: Dict):
        """Update customer display"""
        self.broadcast_to_store(store_id, 'display_update', {
            'display': display_data,
            'timestamp': datetime.now().isoformat()
        }, role='customer')
    
    def get_connected_clients(self, store_id: int = None, role: str = None) -> Dict:
        """Get information about connected clients"""
        if store_id and role:
            room_id = f"store_{store_id}_{role}"
            return {
                'room_id': room_id,
                'client_count': len(self.connected_clients.get(room_id, set()))
            }
        elif store_id:
            # Get all roles for the store
            store_clients = {}
            for role_type in ['staff', 'kitchen', 'customer']:
                room_id = f"store_{store_id}_{role_type}"
                store_clients[role_type] = len(self.connected_clients.get(room_id, set()))
            return store_clients
        else:
            # Get all connected clients
            return {
                room_id: len(clients) 
                for room_id, clients in self.connected_clients.items()
            }
    
    def run(self, host='0.0.0.0', port=5001, debug=False):
        """Run the SocketIO server"""
        if self.socketio and self.app:
            self.socketio.run(self.app, host=host, port=port, debug=debug)

# Global real-time manager instance
realtime_manager = RealTimeManager()

def init_realtime(app: Flask):
    """Initialize real-time support with Flask app"""
    realtime_manager.init_app(app)
    return realtime_manager

# Helper functions for easy integration
def broadcast_new_order(store_id: int, order_data: Dict):
    """Broadcast new order notification"""
    realtime_manager.notify_new_order(store_id, order_data)

def broadcast_order_status(store_id: int, order_id: int, old_status: str, new_status: str, order_data: Dict = None):
    """Broadcast order status change"""
    realtime_manager.notify_order_status_change(store_id, order_id, old_status, new_status, order_data)

def broadcast_menu_update(store_id: int, menu_item_data: Dict, action: str):
    """Broadcast menu update"""
    realtime_manager.notify_menu_update(store_id, menu_item_data, action)

def broadcast_stock_alert(store_id: int, stock_data: Dict, alert_type: str):
    """Broadcast stock alert"""
    realtime_manager.notify_stock_alert(store_id, stock_data, alert_type)

def broadcast_sales_update(store_id: int, sales_data: Dict):
    """Broadcast sales update"""
    realtime_manager.notify_sales_update(store_id, sales_data)

def broadcast_customer_display(store_id: int, display_data: Dict):
    """Broadcast customer display update"""
    realtime_manager.notify_customer_display(store_id, display_data)

def get_realtime_stats(store_id: int = None, role: str = None):
    """Get real-time connection statistics"""
    return realtime_manager.get_connected_clients(store_id, role)

# Example integration with order management
class OrderManager:
    def __init__(self, db_path='pos_database.db'):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def create_order(self, store_id: int, order_data: Dict) -> Dict:
        """Create new order with real-time notification"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert order (simplified)
            cursor.execute("""
                INSERT INTO orders (store_id, table_number, status, total_amount, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                store_id,
                order_data.get('table_number'),
                'pending',
                order_data.get('total_amount', 0),
                datetime.now().isoformat()
            ))
            
            order_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Prepare order data for broadcast
            broadcast_data = {
                'id': order_id,
                'store_id': store_id,
                'table_number': order_data.get('table_number'),
                'status': 'pending',
                'total_amount': order_data.get('total_amount', 0),
                'items': order_data.get('items', []),
                'created_at': datetime.now().isoformat()
            }
            
            # Broadcast new order
            broadcast_new_order(store_id, broadcast_data)
            
            self.logger.info(f"Created order {order_id} for store {store_id}")
            return broadcast_data
            
        except Exception as e:
            self.logger.error(f"Error creating order: {str(e)}")
            return {}
    
    def update_order_status(self, order_id: int, new_status: str) -> bool:
        """Update order status with real-time notification"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current order
            cursor.execute("SELECT store_id, status FROM orders WHERE id = ?", (order_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
            
            store_id, old_status = result
            
            # Update status
            cursor.execute("""
                UPDATE orders SET status = ?, updated_at = ?
                WHERE id = ?
            """, (new_status, datetime.now().isoformat(), order_id))
            
            conn.commit()
            conn.close()
            
            # Broadcast status change
            broadcast_order_status(store_id, order_id, old_status, new_status)
            
            self.logger.info(f"Updated order {order_id} status: {old_status} -> {new_status}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating order status: {str(e)}")
            return False

if __name__ == "__main__":
    # Test WebSocket support
    from flask import Flask
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    # Initialize real-time support
    rt_manager = init_realtime(app)
    
    @app.route('/test')
    def test():
        return "WebSocket test server running"
    
    print("Starting WebSocket test server...")
    rt_manager.run(debug=True)

