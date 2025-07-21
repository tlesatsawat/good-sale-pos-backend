import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from enhanced_caching import cached, cache_invalidate_on_change

class AdvancedMenuManager:
    def __init__(self, db_path='pos_database.db'):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def create_menu_component(self, store_id: int, component_data: Dict) -> Optional[int]:
        """Create a menu component (add-on, topping, etc.)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO menu_components (
                    store_id, name, type, price, is_required, max_selections, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                store_id,
                component_data['name'],
                component_data['type'],  # 'topping', 'size', 'addon', 'modifier'
                component_data.get('price', 0),
                component_data.get('is_required', False),
                component_data.get('max_selections', 1),
                datetime.now().isoformat()
            ))
            
            component_id = cursor.lastrowid
            
            # Add component options if provided
            if 'options' in component_data:
                for option in component_data['options']:
                    cursor.execute("""
                        INSERT INTO menu_component_options (
                            component_id, name, price_modifier, is_default
                        ) VALUES (?, ?, ?, ?)
                    """, (
                        component_id,
                        option['name'],
                        option.get('price_modifier', 0),
                        option.get('is_default', False)
                    ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Created menu component {component_id} for store {store_id}")
            return component_id
            
        except Exception as e:
            self.logger.error(f"Error creating menu component: {str(e)}")
            return None
    
    @cached(ttl=600, key_prefix="menu_components_")
    def get_menu_components(self, store_id: int, component_type: str = None) -> List[Dict]:
        """Get menu components for a store"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = """
                SELECT mc.id, mc.name, mc.type, mc.price, mc.is_required, mc.max_selections,
                       GROUP_CONCAT(
                           json_object(
                               'id', mco.id,
                               'name', mco.name,
                               'price_modifier', mco.price_modifier,
                               'is_default', mco.is_default
                           )
                       ) as options
                FROM menu_components mc
                LEFT JOIN menu_component_options mco ON mc.id = mco.component_id
                WHERE mc.store_id = ?
            """
            
            params = [store_id]
            
            if component_type:
                query += " AND mc.type = ?"
                params.append(component_type)
            
            query += " GROUP BY mc.id ORDER BY mc.type, mc.name"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            conn.close()
            
            components = []
            for row in results:
                component = {
                    'id': row[0],
                    'name': row[1],
                    'type': row[2],
                    'price': float(row[3]),
                    'is_required': bool(row[4]),
                    'max_selections': row[5],
                    'options': []
                }
                
                # Parse options if available
                if row[6]:
                    try:
                        options_str = row[6].split(',')
                        for option_str in options_str:
                            option = json.loads(option_str)
                            component['options'].append(option)
                    except:
                        pass
                
                components.append(component)
            
            return components
            
        except Exception as e:
            self.logger.error(f"Error getting menu components: {str(e)}")
            return []
    
    def link_component_to_menu_item(self, menu_item_id: int, component_id: int, is_required: bool = False) -> bool:
        """Link a component to a menu item"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO menu_item_components (
                    menu_item_id, component_id, is_required
                ) VALUES (?, ?, ?)
            """, (menu_item_id, component_id, is_required))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Linked component {component_id} to menu item {menu_item_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error linking component to menu item: {str(e)}")
            return False
    
    @cached(ttl=600, key_prefix="menu_item_full_")
    def get_menu_item_with_components(self, menu_item_id: int) -> Optional[Dict]:
        """Get menu item with all its components"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get menu item
            cursor.execute("""
                SELECT id, name, description, price, category, is_available
                FROM menu_items WHERE id = ?
            """, (menu_item_id,))
            
            item_result = cursor.fetchone()
            if not item_result:
                return None
            
            menu_item = {
                'id': item_result[0],
                'name': item_result[1],
                'description': item_result[2],
                'price': float(item_result[3]),
                'category': item_result[4],
                'is_available': bool(item_result[5]),
                'components': []
            }
            
            # Get components
            cursor.execute("""
                SELECT mc.id, mc.name, mc.type, mc.price, mc.is_required, mc.max_selections,
                       mic.is_required as item_required,
                       GROUP_CONCAT(
                           json_object(
                               'id', mco.id,
                               'name', mco.name,
                               'price_modifier', mco.price_modifier,
                               'is_default', mco.is_default
                           )
                       ) as options
                FROM menu_item_components mic
                JOIN menu_components mc ON mic.component_id = mc.id
                LEFT JOIN menu_component_options mco ON mc.id = mco.component_id
                WHERE mic.menu_item_id = ?
                GROUP BY mc.id
                ORDER BY mc.type, mc.name
            """, (menu_item_id,))
            
            component_results = cursor.fetchall()
            
            for row in component_results:
                component = {
                    'id': row[0],
                    'name': row[1],
                    'type': row[2],
                    'price': float(row[3]),
                    'is_required': bool(row[4]) or bool(row[6]),  # Component required OR item-specific required
                    'max_selections': row[5],
                    'options': []
                }
                
                # Parse options
                if row[7]:
                    try:
                        options_str = row[7].split(',')
                        for option_str in options_str:
                            option = json.loads(option_str)
                            component['options'].append(option)
                    except:
                        pass
                
                menu_item['components'].append(component)
            
            conn.close()
            return menu_item
            
        except Exception as e:
            self.logger.error(f"Error getting menu item with components: {str(e)}")
            return None
    
    def calculate_item_price(self, menu_item_id: int, selected_options: Dict) -> float:
        """Calculate total price for menu item with selected options"""
        try:
            menu_item = self.get_menu_item_with_components(menu_item_id)
            if not menu_item:
                return 0.0
            
            total_price = menu_item['price']
            
            # Add component prices
            for component in menu_item['components']:
                component_id = str(component['id'])
                
                if component_id in selected_options:
                    selected_option_ids = selected_options[component_id]
                    
                    if not isinstance(selected_option_ids, list):
                        selected_option_ids = [selected_option_ids]
                    
                    for option in component['options']:
                        if option['id'] in selected_option_ids:
                            total_price += option['price_modifier']
            
            return round(total_price, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating item price: {str(e)}")
            return 0.0
    
    @cache_invalidate_on_change(patterns=["menu_", "menu_components_", "menu_item_full_"])
    def create_menu_item_with_components(self, store_id: int, item_data: Dict, component_links: List[Dict] = None) -> Optional[int]:
        """Create menu item and link components"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create menu item
            cursor.execute("""
                INSERT INTO menu_items (
                    store_id, name, description, price, category, is_available, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                store_id,
                item_data['name'],
                item_data.get('description', ''),
                item_data['price'],
                item_data.get('category', 'main'),
                item_data.get('is_available', True),
                datetime.now().isoformat()
            ))
            
            menu_item_id = cursor.lastrowid
            
            # Link components if provided
            if component_links:
                for link in component_links:
                    cursor.execute("""
                        INSERT INTO menu_item_components (
                            menu_item_id, component_id, is_required
                        ) VALUES (?, ?, ?)
                    """, (
                        menu_item_id,
                        link['component_id'],
                        link.get('is_required', False)
                    ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Created menu item {menu_item_id} with components for store {store_id}")
            return menu_item_id
            
        except Exception as e:
            self.logger.error(f"Error creating menu item with components: {str(e)}")
            return None
    
    def get_menu_pricing_tiers(self, store_id: int) -> List[Dict]:
        """Get pricing tiers for dynamic pricing"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, multiplier, start_time, end_time, days_of_week, is_active
                FROM pricing_tiers 
                WHERE store_id = ? AND is_active = 1
                ORDER BY name
            """, (store_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            tiers = []
            for row in results:
                tier = {
                    'id': row[0],
                    'name': row[1],
                    'multiplier': float(row[2]),
                    'start_time': row[3],
                    'end_time': row[4],
                    'days_of_week': json.loads(row[5]) if row[5] else [],
                    'is_active': bool(row[6])
                }
                tiers.append(tier)
            
            return tiers
            
        except Exception as e:
            self.logger.error(f"Error getting pricing tiers: {str(e)}")
            return []
    
    def apply_pricing_tier(self, base_price: float, tier_id: int) -> float:
        """Apply pricing tier to base price"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT multiplier FROM pricing_tiers 
                WHERE id = ? AND is_active = 1
            """, (tier_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                multiplier = float(result[0])
                return round(base_price * multiplier, 2)
            
            return base_price
            
        except Exception as e:
            self.logger.error(f"Error applying pricing tier: {str(e)}")
            return base_price

# Table Management System
class TableManager:
    def __init__(self, db_path='pos_database.db'):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def create_table(self, store_id: int, table_data: Dict) -> Optional[int]:
        """Create a new table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO tables (
                    store_id, table_number, capacity, section, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                store_id,
                table_data['table_number'],
                table_data.get('capacity', 4),
                table_data.get('section', 'main'),
                'available',
                datetime.now().isoformat()
            ))
            
            table_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            self.logger.info(f"Created table {table_id} for store {store_id}")
            return table_id
            
        except Exception as e:
            self.logger.error(f"Error creating table: {str(e)}")
            return None
    
    @cached(ttl=60, key_prefix="tables_")
    def get_tables(self, store_id: int, section: str = None) -> List[Dict]:
        """Get tables for a store"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = """
                SELECT t.id, t.table_number, t.capacity, t.section, t.status,
                       o.id as order_id, o.total_amount, o.created_at as order_time
                FROM tables t
                LEFT JOIN orders o ON t.id = o.table_id AND o.status IN ('pending', 'preparing', 'ready')
                WHERE t.store_id = ?
            """
            
            params = [store_id]
            
            if section:
                query += " AND t.section = ?"
                params.append(section)
            
            query += " ORDER BY t.section, t.table_number"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            conn.close()
            
            tables = []
            for row in results:
                table = {
                    'id': row[0],
                    'table_number': row[1],
                    'capacity': row[2],
                    'section': row[3],
                    'status': row[4],
                    'current_order': None
                }
                
                if row[5]:  # Has active order
                    table['current_order'] = {
                        'id': row[5],
                        'total_amount': float(row[6]),
                        'order_time': row[7]
                    }
                    table['status'] = 'occupied'
                
                tables.append(table)
            
            return tables
            
        except Exception as e:
            self.logger.error(f"Error getting tables: {str(e)}")
            return []
    
    def merge_tables(self, table_ids: List[int], primary_table_id: int) -> bool:
        """Merge multiple tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update all orders to use primary table
            cursor.execute("""
                UPDATE orders SET table_id = ?
                WHERE table_id IN ({}) AND status IN ('pending', 'preparing', 'ready')
            """.format(','.join('?' * len(table_ids))), [primary_table_id] + table_ids)
            
            # Mark non-primary tables as merged
            other_table_ids = [tid for tid in table_ids if tid != primary_table_id]
            if other_table_ids:
                cursor.execute("""
                    UPDATE tables SET status = 'merged', merged_with = ?
                    WHERE id IN ({})
                """.format(','.join('?' * len(other_table_ids))), [primary_table_id] + other_table_ids)
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Merged tables {table_ids} into primary table {primary_table_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error merging tables: {str(e)}")
            return False
    
    def split_bill(self, order_id: int, split_items: List[Dict]) -> List[int]:
        """Split bill into multiple orders"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get original order
            cursor.execute("""
                SELECT store_id, table_id, total_amount
                FROM orders WHERE id = ?
            """, (order_id,))
            
            original_order = cursor.fetchone()
            if not original_order:
                return []
            
            store_id, table_id, original_total = original_order
            
            new_order_ids = []
            
            # Create new orders for each split
            for split in split_items:
                cursor.execute("""
                    INSERT INTO orders (
                        store_id, table_id, total_amount, status, created_at, split_from
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    store_id,
                    table_id,
                    split['total_amount'],
                    'pending',
                    datetime.now().isoformat(),
                    order_id
                ))
                
                new_order_id = cursor.lastrowid
                new_order_ids.append(new_order_id)
                
                # Add items to new order
                for item in split['items']:
                    cursor.execute("""
                        INSERT INTO order_items (
                            order_id, menu_item_id, quantity, unit_price, customizations
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        new_order_id,
                        item['menu_item_id'],
                        item['quantity'],
                        item['unit_price'],
                        json.dumps(item.get('customizations', {}))
                    ))
            
            # Mark original order as split
            cursor.execute("""
                UPDATE orders SET status = 'split' WHERE id = ?
            """, (order_id,))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Split order {order_id} into {len(new_order_ids)} new orders")
            return new_order_ids
            
        except Exception as e:
            self.logger.error(f"Error splitting bill: {str(e)}")
            return []

if __name__ == "__main__":
    # Test advanced menu management
    logging.basicConfig(level=logging.INFO)
    
    menu_manager = AdvancedMenuManager()
    table_manager = TableManager()
    
    print("Testing advanced menu management...")
    
    # Test getting menu components
    components = menu_manager.get_menu_components(1)
    print(f"Menu components: {len(components)}")
    
    # Test getting tables
    tables = table_manager.get_tables(1)
    print(f"Tables: {len(tables)}")

