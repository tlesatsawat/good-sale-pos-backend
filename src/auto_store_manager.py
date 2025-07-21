import schedule
import time
import threading
import logging
import json
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, Optional
import sqlite3
from ai_analysis import AIAnalysisEngine

class AutoStoreManager:
    def __init__(self, db_path='pos_database.db'):
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self.ai_engine = AIAnalysisEngine(db_path)
        self.auto_close_settings = {}
        self.scheduler_running = False
        self.scheduler_thread = None
        
    def start_scheduler(self):
        """เริ่มต้น scheduler สำหรับการปิดร้านอัตโนมัติ"""
        if not self.scheduler_running:
            self.scheduler_running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            self.logger.info("Auto store close scheduler started")
    
    def stop_scheduler(self):
        """หยุด scheduler"""
        self.scheduler_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
        self.logger.info("Auto store close scheduler stopped")
    
    def _run_scheduler(self):
        """รัน scheduler ในพื้นหลัง"""
        while self.scheduler_running:
            schedule.run_pending()
            time.sleep(60)  # ตรวจสอบทุกนาที
    
    def set_auto_close_time(self, store_id: int, close_time: str, enabled: bool = True) -> bool:
        """ตั้งเวลาปิดร้านอัตโนมัติ"""
        try:
            # ตรวจสอบรูปแบบเวลา (HH:MM)
            try:
                close_time_obj = datetime.strptime(close_time, '%H:%M').time()
            except ValueError:
                self.logger.error(f"Invalid time format: {close_time}")
                return False
            
            # บันทึกการตั้งค่า
            self.auto_close_settings[store_id] = {
                'close_time': close_time,
                'enabled': enabled,
                'updated_at': datetime.now().isoformat()
            }
            
            # ลบ job เก่า
            schedule.clear(f'auto_close_{store_id}')
            
            # เพิ่ม job ใหม่
            if enabled:
                schedule.every().day.at(close_time).do(
                    self._auto_close_store, store_id
                ).tag(f'auto_close_{store_id}')
                
                self.logger.info(f"Auto close scheduled for store {store_id} at {close_time}")
            
            # บันทึกลงฐานข้อมูล
            self._save_auto_close_setting(store_id, close_time, enabled)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting auto close time: {e}")
            return False
    
    def _auto_close_store(self, store_id: int):
        """ปิดร้านอัตโนมัติ"""
        try:
            # ตรวจสอบว่าร้านเปิดอยู่หรือไม่
            if not self._is_store_open(store_id):
                self.logger.info(f"Store {store_id} is already closed")
                return
            
            # สร้างสรุปยอดขายก่อนปิดร้าน
            daily_summary = self.generate_daily_summary(store_id)
            
            # ปิดร้าน
            success = self._close_store(store_id, auto_close=True)
            
            if success:
                self.logger.info(f"Store {store_id} automatically closed at {datetime.now()}")
                
                # บันทึกสรุปยอดขาย
                self._save_daily_summary(store_id, daily_summary)
            else:
                self.logger.error(f"Failed to auto close store {store_id}")
                
        except Exception as e:
            self.logger.error(f"Error in auto close store {store_id}: {e}")
    
    def generate_daily_summary(self, store_id: int, target_date: str = None) -> Dict:
        """สร้างสรุปยอดขายรายวัน"""
        try:
            if target_date is None:
                target_date = datetime.now().date()
            else:
                target_date = datetime.fromisoformat(target_date).date()
            
            # ดึงข้อมูลยอดขายวันนี้
            daily_analysis = self.ai_engine.analyze_daily_sales(target_date)
            
            # ดึงข้อมูลเมนูขายดี
            menu_analysis = self.ai_engine.analyze_menu_performance(1)  # วันนี้เท่านั้น
            
            # ดึงคำแนะนำวัตถุดิบสำหรับพรุ่งนี้
            ingredient_recommendations = self.ai_engine.predict_ingredient_needs(1)
            
            # สร้างข้อความอวยพรและคำแนะนำ
            blessing_message = self._generate_blessing_message()
            ai_recommendations = self._generate_ai_recommendations(daily_analysis, menu_analysis, ingredient_recommendations)
            
            summary = {
                'store_id': store_id,
                'date': target_date.isoformat(),
                'daily_analysis': daily_analysis,
                'menu_analysis': menu_analysis,
                'ingredient_recommendations': ingredient_recommendations,
                'blessing_message': blessing_message,
                'ai_recommendations': ai_recommendations,
                'generated_at': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating daily summary: {e}")
            return {}
    
    def generate_opening_summary(self, store_id: int) -> Dict:
        """สร้างสรุปข้อมูลเมื่อเปิดร้าน"""
        try:
            # ข้อความอวยพรเปิดร้าน
            opening_message = self._generate_opening_message()
            
            # ดึงข้อมูลยอดขายเมื่อวาน
            yesterday = datetime.now().date() - timedelta(days=1)
            yesterday_analysis = self.ai_engine.analyze_daily_sales(yesterday)
            
            # คำแนะนำสำหรับวันนี้
            today_recommendations = self._generate_today_recommendations(yesterday_analysis)
            
            summary = {
                'store_id': store_id,
                'date': datetime.now().date().isoformat(),
                'opening_message': opening_message,
                'yesterday_analysis': yesterday_analysis,
                'today_recommendations': today_recommendations,
                'generated_at': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating opening summary: {e}")
            return {}
    
    def _generate_blessing_message(self) -> str:
        """สร้างข้อความอวยพรปิดร้าน"""
        messages = [
            "🌟 ขอบคุณสำหรับการทำงานหนักวันนี้! พรุ่งนี้จะเป็นวันที่ดีกว่านี้",
            "💪 วันนี้ผ่านไปด้วยดี ขอให้พักผ่อนให้เพียงพอ แล้วพบกันใหม่พรุ่งนี้",
            "🙏 ขอบคุณที่ให้บริการลูกค้าด้วยใจ วันนี้เป็นอีกวันที่ประสบความสำเร็จ",
            "✨ การทำงานหนักของวันนี้จะนำมาซึ่งผลลัพธ์ที่ดีในอนาคต",
            "🌙 ขอให้มีความสุขกับการพักผ่อน และตื่นมาพร้อมพลังใหม่พรุ่งนี้"
        ]
        
        import random
        return random.choice(messages)
    
    def _generate_opening_message(self) -> str:
        """สร้างข้อความอวยพรเปิดร้าน"""
        weekday = datetime.now().weekday()
        day_names = ['จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์', 'อาทิตย์']
        
        messages = [
            f"🌅 สวัสดีตอนเช้า! ขอให้วัน{day_names[weekday]}นี้เป็นวันที่ดีและประสบความสำเร็จ",
            f"☀️ เริ่มต้นวัน{day_names[weekday]}ด้วยพลังบวก ขอให้มีลูกค้าเยอะๆ วันนี้",
            f"🎯 วัน{day_names[weekday]}ใหม่มาถึงแล้ว! พร้อมที่จะสร้างยอดขายที่ดีกันไหม",
            f"💫 ขอให้วัน{day_names[weekday]}นี้เต็มไปด้วยโอกาสดีๆ และความสำเร็จ",
            f"🚀 เริ่มต้นวัน{day_names[weekday]}ด้วยความมุ่งมั่น ขอให้ทุกอย่างเป็นไปตามที่หวัง"
        ]
        
        import random
        return random.choice(messages)
    
    def _generate_ai_recommendations(self, daily_analysis: Dict, menu_analysis: Dict, ingredient_recommendations: Dict) -> list:
        """สร้างคำแนะนำ AI"""
        recommendations = []
        
        if daily_analysis:
            revenue = daily_analysis.get('total_revenue', 0)
            orders = daily_analysis.get('total_orders', 0)
            change = daily_analysis.get('revenue_change_percent', 0)
            
            if revenue > 0:
                recommendations.append(f"📊 วันนี้ยอดขายรวม {revenue:,.2f} บาท จากออร์เดอร์ {orders} รายการ")
                
                if change > 5:
                    recommendations.append(f"📈 ยอดขายเพิ่มขึ้น {change:.1f}% เมื่อเทียบกับเมื่อวาน - ทำได้ดีมาก!")
                elif change < -5:
                    recommendations.append(f"📉 ยอดขายลดลง {abs(change):.1f}% - พรุ่งนี้ลองทำโปรโมชั่นดูไหม")
        
        if menu_analysis and menu_analysis.get('top_sellers'):
            top_item = menu_analysis['top_sellers'][0]
            recommendations.append(f"🏆 เมนูขายดีที่สุดวันนี้: '{top_item['menu_name']}' ขายได้ {top_item['total_sold']} รายการ")
        
        if ingredient_recommendations and ingredient_recommendations.get('recommendations'):
            urgent_count = len([r for r in ingredient_recommendations['recommendations'] if r['shortage'] > r['current_stock']])
            if urgent_count > 0:
                recommendations.append(f"⚠️ มีวัตถุดิบ {urgent_count} รายการที่ต้องสั่งเพิ่มด่วนสำหรับพรุ่งนี้")
        
        return recommendations
    
    def _generate_today_recommendations(self, yesterday_analysis: Dict) -> list:
        """สร้างคำแนะนำสำหรับวันนี้"""
        recommendations = []
        
        if yesterday_analysis:
            revenue = yesterday_analysis.get('total_revenue', 0)
            change = yesterday_analysis.get('revenue_change_percent', 0)
            
            if revenue > 0:
                recommendations.append(f"📊 เมื่อวานยอดขาย {revenue:,.2f} บาท")
                
                if change > 0:
                    recommendations.append("🎯 เมื่อวานยอดขายดี วันนี้พยายามรักษาระดับนี้ไว้")
                else:
                    recommendations.append("💪 วันนี้เป็นโอกาสดีที่จะทำยอดขายให้ดีกว่าเมื่อวาน")
        
        # คำแนะนำทั่วไป
        weekday = datetime.now().weekday()
        if weekday in [5, 6]:  # วันเสาร์-อาทิตย์
            recommendations.append("🎉 วันหยุดมักมีลูกค้าเยอะ เตรียมพร้อมรับออร์เดอร์เยอะๆ")
        elif weekday == 0:  # วันจันทร์
            recommendations.append("☕ วันจันทร์คนมักดื่มกาแฟเยอะ เตรียมเครื่องดื่มให้พร้อม")
        
        return recommendations
    
    def _is_store_open(self, store_id: int) -> bool:
        """ตรวจสอบว่าร้านเปิดอยู่หรือไม่"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT is_open FROM stores WHERE id = ?
            """, (store_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else False
            
        except Exception as e:
            self.logger.error(f"Error checking store status: {e}")
            return False
    
    def _close_store(self, store_id: int, auto_close: bool = False) -> bool:
        """ปิดร้าน"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE stores 
                SET is_open = 0, 
                    last_closed_at = ?,
                    auto_closed = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), auto_close, store_id))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error closing store: {e}")
            return False
    
    def _save_auto_close_setting(self, store_id: int, close_time: str, enabled: bool):
        """บันทึกการตั้งค่าปิดร้านอัตโนมัติ"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO auto_close_settings 
                (store_id, close_time, enabled, updated_at)
                VALUES (?, ?, ?, ?)
            """, (store_id, close_time, enabled, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error saving auto close setting: {e}")
    
    def _save_daily_summary(self, store_id: int, summary: Dict):
        """บันทึกสรุปยอดขายรายวัน"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO daily_summaries 
                (store_id, date, summary_data, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                store_id, 
                summary.get('date'), 
                json.dumps(summary, ensure_ascii=False),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error saving daily summary: {e}")
    
    def get_auto_close_settings(self, store_id: int) -> Dict:
        """ดึงการตั้งค่าปิดร้านอัตโนมัติ"""
        try:
            return self.auto_close_settings.get(store_id, {
                'close_time': '22:00',
                'enabled': False,
                'updated_at': None
            })
            
        except Exception as e:
            self.logger.error(f"Error getting auto close settings: {e}")
            return {}
    
    def load_auto_close_settings(self):
        """โหลดการตั้งค่าปิดร้านอัตโนมัติจากฐานข้อมูล"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT store_id, close_time, enabled, updated_at 
                FROM auto_close_settings 
                WHERE enabled = 1
            """)
            
            settings = cursor.fetchall()
            conn.close()
            
            for setting in settings:
                store_id, close_time, enabled, updated_at = setting
                self.set_auto_close_time(store_id, close_time, enabled)
            
            self.logger.info(f"Loaded {len(settings)} auto close settings")
            
        except Exception as e:
            self.logger.error(f"Error loading auto close settings: {e}")

# สร้าง instance global
auto_store_manager = AutoStoreManager()

