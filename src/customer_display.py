import logging
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class CustomerDisplayManager:
    def __init__(self, db_path='pos_database.db'):
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self.active_advertisements = []
        self.display_settings = {}
        
    def get_display_content(self, store_id: int) -> Dict:
        """ดึงเนื้อหาสำหรับแสดงบนจอลูกค้า"""
        try:
            # ดึงการตั้งค่าการแสดงผล
            settings = self.get_display_settings(store_id)
            
            # ดึงโฆษณาที่กำลังแสดง
            advertisements = self.get_active_advertisements(store_id)
            
            # ดึงข้อมูลร้าน
            store_info = self._get_store_info(store_id)
            
            # ดึงเมนูแนะนำ
            featured_menu = self._get_featured_menu(store_id)
            
            # ดึงโปรโมชั่นปัจจุบัน
            promotions = self._get_current_promotions(store_id)
            
            # ดึงข้อมูลคิวปัจจุบัน
            queue_info = self._get_queue_info(store_id)
            
            content = {
                'store_info': store_info,
                'advertisements': advertisements,
                'featured_menu': featured_menu,
                'promotions': promotions,
                'queue_info': queue_info,
                'settings': settings,
                'last_updated': datetime.now().isoformat()
            }
            
            return content
            
        except Exception as e:
            self.logger.error(f"Error getting display content: {e}")
            return {}
    
    def add_advertisement(self, store_id: int, ad_data: Dict) -> bool:
        """เพิ่มโฆษณาใหม่"""
        try:
            # ตรวจสอบข้อมูลที่จำเป็น
            required_fields = ['title', 'content', 'display_duration']
            for field in required_fields:
                if field not in ad_data:
                    self.logger.error(f"Missing required field: {field}")
                    return False
            
            # เพิ่มข้อมูลเพิ่มเติม
            ad_data.update({
                'store_id': store_id,
                'created_at': datetime.now().isoformat(),
                'is_active': True,
                'display_count': 0
            })
            
            # บันทึกลงฐานข้อมูล
            success = self._save_advertisement(ad_data)
            
            if success:
                self.logger.info(f"Advertisement added for store {store_id}: {ad_data['title']}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error adding advertisement: {e}")
            return False
    
    def update_advertisement(self, ad_id: int, ad_data: Dict) -> bool:
        """อัปเดตโฆษณา"""
        try:
            ad_data['updated_at'] = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # สร้าง SQL query แบบ dynamic
            set_clauses = []
            values = []
            
            for key, value in ad_data.items():
                if key != 'id':
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            values.append(ad_id)
            
            cursor.execute(f"""
                UPDATE advertisements 
                SET {', '.join(set_clauses)}
                WHERE id = ?
            """, values)
            
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating advertisement: {e}")
            return False
    
    def delete_advertisement(self, ad_id: int) -> bool:
        """ลบโฆษณา"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM advertisements WHERE id = ?", (ad_id,))
            
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error deleting advertisement: {e}")
            return False
    
    def get_active_advertisements(self, store_id: int) -> List[Dict]:
        """ดึงโฆษณาที่กำลังแสดง"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM advertisements 
                WHERE store_id = ? AND is_active = 1
                ORDER BY priority DESC, created_at DESC
            """, (store_id,))
            
            columns = [description[0] for description in cursor.description]
            advertisements = []
            
            for row in cursor.fetchall():
                ad = dict(zip(columns, row))
                
                # ตรวจสอบว่าโฆษณายังไม่หมดอายุ
                if ad.get('end_date'):
                    end_date = datetime.fromisoformat(ad['end_date'])
                    if datetime.now() > end_date:
                        # ปิดการใช้งานโฆษณาที่หมดอายุ
                        self.update_advertisement(ad['id'], {'is_active': False})
                        continue
                
                advertisements.append(ad)
            
            conn.close()
            return advertisements
            
        except Exception as e:
            self.logger.error(f"Error getting active advertisements: {e}")
            return []
    
    def set_display_settings(self, store_id: int, settings: Dict) -> bool:
        """ตั้งค่าการแสดงผล"""
        try:
            self.display_settings[store_id] = {
                **settings,
                'updated_at': datetime.now().isoformat()
            }
            
            # บันทึกลงฐานข้อมูล
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO display_settings 
                (store_id, settings_data, updated_at)
                VALUES (?, ?, ?)
            """, (
                store_id,
                json.dumps(settings, ensure_ascii=False),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting display settings: {e}")
            return False
    
    def get_display_settings(self, store_id: int) -> Dict:
        """ดึงการตั้งค่าการแสดงผล"""
        try:
            # ตรวจสอบใน memory ก่อน
            if store_id in self.display_settings:
                return self.display_settings[store_id]
            
            # ดึงจากฐานข้อมูล
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT settings_data FROM display_settings 
                WHERE store_id = ?
            """, (store_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                settings = json.loads(result[0])
                self.display_settings[store_id] = settings
                return settings
            else:
                # ใช้การตั้งค่าเริ่มต้น
                default_settings = {
                    'theme': 'modern',
                    'background_color': '#f8f9fa',
                    'text_color': '#212529',
                    'accent_color': '#007bff',
                    'font_size': 'medium',
                    'animation_enabled': True,
                    'show_queue': True,
                    'show_promotions': True,
                    'show_featured_menu': True,
                    'advertisement_interval': 5000,  # milliseconds
                    'auto_scroll': True
                }
                
                self.set_display_settings(store_id, default_settings)
                return default_settings
                
        except Exception as e:
            self.logger.error(f"Error getting display settings: {e}")
            return {}
    
    def _get_store_info(self, store_id: int) -> Dict:
        """ดึงข้อมูลร้าน"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT name, description, logo_url, phone, address 
                FROM stores WHERE id = ?
            """, (store_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'name': result[0],
                    'description': result[1],
                    'logo_url': result[2],
                    'phone': result[3],
                    'address': result[4]
                }
            else:
                return {
                    'name': 'GOOD SALE POS',
                    'description': 'ระบบ POS ที่ดีที่สุด',
                    'logo_url': None,
                    'phone': '02-xxx-xxxx',
                    'address': 'กรุงเทพมหานคร'
                }
                
        except Exception as e:
            self.logger.error(f"Error getting store info: {e}")
            return {}
    
    def _get_featured_menu(self, store_id: int, limit: int = 6) -> List[Dict]:
        """ดึงเมนูแนะนำ"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # ดึงเมนูที่ขายดีหรือเมนูที่ตั้งเป็นแนะนำ
            cursor.execute("""
                SELECT m.id, m.name, m.price, m.description, m.image_url,
                       COALESCE(SUM(oi.quantity), 0) as total_sold
                FROM menu_items m
                LEFT JOIN order_items oi ON m.id = oi.menu_item_id
                LEFT JOIN orders o ON oi.order_id = o.id
                WHERE m.store_id = ? AND m.is_available = 1
                  AND (o.created_at >= date('now', '-7 days') OR o.created_at IS NULL)
                GROUP BY m.id
                ORDER BY m.is_featured DESC, total_sold DESC
                LIMIT ?
            """, (store_id, limit))
            
            columns = [description[0] for description in cursor.description]
            featured_menu = []
            
            for row in cursor.fetchall():
                menu_item = dict(zip(columns, row))
                featured_menu.append(menu_item)
            
            conn.close()
            return featured_menu
            
        except Exception as e:
            self.logger.error(f"Error getting featured menu: {e}")
            return []
    
    def _get_current_promotions(self, store_id: int) -> List[Dict]:
        """ดึงโปรโมชั่นปัจจุบัน"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            current_date = datetime.now().date().isoformat()
            
            cursor.execute("""
                SELECT * FROM promotions 
                WHERE store_id = ? AND is_active = 1
                  AND start_date <= ? AND end_date >= ?
                ORDER BY priority DESC, created_at DESC
            """, (store_id, current_date, current_date))
            
            columns = [description[0] for description in cursor.description]
            promotions = []
            
            for row in cursor.fetchall():
                promotion = dict(zip(columns, row))
                promotions.append(promotion)
            
            conn.close()
            return promotions
            
        except Exception as e:
            self.logger.error(f"Error getting current promotions: {e}")
            return []
    
    def _get_queue_info(self, store_id: int) -> Dict:
        """ดึงข้อมูลคิวปัจจุบัน"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # ดึงคิวที่รอ
            cursor.execute("""
                SELECT COUNT(*) FROM orders 
                WHERE store_id = ? AND status IN ('pending', 'preparing')
                  AND DATE(created_at) = DATE('now')
            """, (store_id,))
            
            pending_orders = cursor.fetchone()[0]
            
            # ดึงเวลารอโดยเฉลี่ย
            cursor.execute("""
                SELECT AVG(
                    (julianday(completed_at) - julianday(created_at)) * 24 * 60
                ) as avg_wait_minutes
                FROM orders 
                WHERE store_id = ? AND status = 'completed'
                  AND DATE(created_at) = DATE('now')
                  AND completed_at IS NOT NULL
            """, (store_id,))
            
            avg_wait = cursor.fetchone()[0] or 15  # default 15 minutes
            
            conn.close()
            
            return {
                'pending_orders': pending_orders,
                'estimated_wait_minutes': int(avg_wait),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting queue info: {e}")
            return {
                'pending_orders': 0,
                'estimated_wait_minutes': 15,
                'last_updated': datetime.now().isoformat()
            }
    
    def _save_advertisement(self, ad_data: Dict) -> bool:
        """บันทึกโฆษณาลงฐานข้อมูล"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO advertisements 
                (store_id, title, content, image_url, display_duration, 
                 priority, start_date, end_date, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ad_data['store_id'],
                ad_data['title'],
                ad_data['content'],
                ad_data.get('image_url'),
                ad_data['display_duration'],
                ad_data.get('priority', 1),
                ad_data.get('start_date'),
                ad_data.get('end_date'),
                ad_data['is_active'],
                ad_data['created_at']
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving advertisement: {e}")
            return False
    
    def increment_display_count(self, ad_id: int) -> bool:
        """เพิ่มจำนวนครั้งที่แสดงโฆษณา"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE advertisements 
                SET display_count = display_count + 1,
                    last_displayed_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), ad_id))
            
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error incrementing display count: {e}")
            return False

# สร้าง instance global
customer_display_manager = CustomerDisplayManager()

