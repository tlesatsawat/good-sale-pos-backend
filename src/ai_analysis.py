import sqlite3
import json
import logging
from datetime import datetime, timedelta, date
from collections import defaultdict, Counter
import statistics

class AIAnalysisEngine:
    def __init__(self, db_path='pos_database.db'):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def get_db_connection(self):
        """สร้างการเชื่อมต่อฐานข้อมูล"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def analyze_daily_sales(self, target_date=None):
        """วิเคราะห์ยอดขายรายวัน"""
        if target_date is None:
            target_date = date.today()
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # ดึงข้อมูลยอดขายวันนี้
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(total_amount) as total_revenue,
                    AVG(total_amount) as avg_order_value,
                    MIN(total_amount) as min_order,
                    MAX(total_amount) as max_order
                FROM orders 
                WHERE DATE(created_at) = ?
                AND status != 'cancelled'
            """, (target_date,))
            
            daily_stats = cursor.fetchone()
            
            # ดึงข้อมูลยอดขายตามช่วงเวลา
            cursor.execute("""
                SELECT 
                    strftime('%H', created_at) as hour,
                    COUNT(*) as order_count,
                    SUM(total_amount) as revenue
                FROM orders 
                WHERE DATE(created_at) = ?
                AND status != 'cancelled'
                GROUP BY strftime('%H', created_at)
                ORDER BY hour
            """, (target_date,))
            
            hourly_stats = cursor.fetchall()
            
            # เปรียบเทียบกับวันก่อนหน้า
            yesterday = target_date - timedelta(days=1)
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(total_amount) as total_revenue
                FROM orders 
                WHERE DATE(created_at) = ?
                AND status != 'cancelled'
            """, (yesterday,))
            
            yesterday_stats = cursor.fetchone()
            
            conn.close()
            
            # คำนวณการเปลี่ยนแปลง
            revenue_change = 0
            order_change = 0
            
            if yesterday_stats and yesterday_stats['total_revenue']:
                revenue_change = ((daily_stats['total_revenue'] or 0) - (yesterday_stats['total_revenue'] or 0)) / yesterday_stats['total_revenue'] * 100
                order_change = ((daily_stats['total_orders'] or 0) - (yesterday_stats['total_orders'] or 0)) / yesterday_stats['total_orders'] * 100
            
            return {
                'date': target_date.isoformat(),
                'total_orders': daily_stats['total_orders'] or 0,
                'total_revenue': daily_stats['total_revenue'] or 0,
                'avg_order_value': daily_stats['avg_order_value'] or 0,
                'min_order': daily_stats['min_order'] or 0,
                'max_order': daily_stats['max_order'] or 0,
                'revenue_change_percent': round(revenue_change, 2),
                'order_change_percent': round(order_change, 2),
                'hourly_breakdown': [dict(row) for row in hourly_stats],
                'peak_hour': max(hourly_stats, key=lambda x: x['order_count'])['hour'] if hourly_stats else None
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing daily sales: {e}")
            return None
    
    def analyze_menu_performance(self, days=7):
        """วิเคราะห์ประสิทธิภาพเมนู"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            start_date = date.today() - timedelta(days=days)
            
            # ดึงข้อมูลเมนูขายดี
            cursor.execute("""
                SELECT 
                    oi.menu_item_id,
                    mi.name as menu_name,
                    mi.price,
                    mi.category,
                    SUM(oi.quantity) as total_sold,
                    SUM(oi.quantity * oi.price) as total_revenue,
                    COUNT(DISTINCT oi.order_id) as order_frequency,
                    AVG(oi.quantity) as avg_quantity_per_order
                FROM order_items oi
                JOIN menu_items mi ON oi.menu_item_id = mi.id
                JOIN orders o ON oi.order_id = o.id
                WHERE DATE(o.created_at) >= ?
                AND o.status != 'cancelled'
                GROUP BY oi.menu_item_id, mi.name, mi.price, mi.category
                ORDER BY total_sold DESC
            """, (start_date,))
            
            menu_performance = cursor.fetchall()
            
            # คำนวณ metrics เพิ่มเติม
            total_items_sold = sum(item['total_sold'] for item in menu_performance)
            total_revenue = sum(item['total_revenue'] for item in menu_performance)
            
            enhanced_performance = []
            for item in menu_performance:
                item_dict = dict(item)
                item_dict['sales_percentage'] = (item['total_sold'] / total_items_sold * 100) if total_items_sold > 0 else 0
                item_dict['revenue_percentage'] = (item['total_revenue'] / total_revenue * 100) if total_revenue > 0 else 0
                item_dict['profit_margin'] = item['price'] * 0.6  # สมมติ profit margin 60%
                item_dict['total_profit'] = item_dict['profit_margin'] * item['total_sold']
                enhanced_performance.append(item_dict)
            
            # หาเมนูขายดี top 10
            top_sellers = enhanced_performance[:10]
            
            # หาเมนูที่ขายได้น้อย (bottom 10)
            poor_performers = enhanced_performance[-10:] if len(enhanced_performance) > 10 else []
            
            # วิเคราะห์ตามหมวดหมู่
            category_performance = defaultdict(lambda: {'total_sold': 0, 'total_revenue': 0, 'item_count': 0})
            for item in enhanced_performance:
                cat = item['category'] or 'Other'
                category_performance[cat]['total_sold'] += item['total_sold']
                category_performance[cat]['total_revenue'] += item['total_revenue']
                category_performance[cat]['item_count'] += 1
            
            conn.close()
            
            return {
                'analysis_period': f"{start_date.isoformat()} to {date.today().isoformat()}",
                'total_items_analyzed': len(enhanced_performance),
                'total_items_sold': total_items_sold,
                'total_revenue': total_revenue,
                'top_sellers': top_sellers,
                'poor_performers': poor_performers,
                'category_performance': dict(category_performance),
                'insights': self._generate_menu_insights(enhanced_performance)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing menu performance: {e}")
            return None
    
    def _generate_menu_insights(self, menu_data):
        """สร้าง insights จากข้อมูลเมนู"""
        insights = []
        
        if not menu_data:
            return insights
        
        # หาเมนูที่มี profit margin สูงสุด
        highest_profit = max(menu_data, key=lambda x: x['total_profit'])
        insights.append(f"เมนู '{highest_profit['menu_name']}' ให้กำไรสูงสุด {highest_profit['total_profit']:.2f} บาท")
        
        # หาเมนูที่ขายดีที่สุด
        best_seller = menu_data[0] if menu_data else None
        if best_seller:
            insights.append(f"เมนูขายดีที่สุดคือ '{best_seller['menu_name']}' ขายได้ {best_seller['total_sold']} รายการ")
        
        # วิเคราะห์ราคาเฉลี่ย
        avg_price = statistics.mean([item['price'] for item in menu_data])
        insights.append(f"ราคาเฉลี่ยของเมนูคือ {avg_price:.2f} บาท")
        
        # หาเมนูที่มีความถี่ในการสั่งสูง
        high_frequency = [item for item in menu_data if item['order_frequency'] > 10]
        if high_frequency:
            insights.append(f"มีเมนู {len(high_frequency)} รายการที่ปรากฏในออร์เดอร์บ่อยครั้ง (มากกว่า 10 ครั้ง)")
        
        return insights
    
    def predict_ingredient_needs(self, days_ahead=1):
        """ทำนายความต้องการวัตถุดิบ"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # ดึงข้อมูลการใช้วัตถุดิบในอดีต 7 วัน
            start_date = date.today() - timedelta(days=7)
            
            cursor.execute("""
                SELECT 
                    mi.name as menu_name,
                    mi.ingredients,
                    SUM(oi.quantity) as total_sold
                FROM order_items oi
                JOIN menu_items mi ON oi.menu_item_id = mi.id
                JOIN orders o ON oi.order_id = o.id
                WHERE DATE(o.created_at) >= ?
                AND o.status != 'cancelled'
                GROUP BY oi.menu_item_id, mi.name, mi.ingredients
            """, (start_date,))
            
            menu_usage = cursor.fetchall()
            
            # คำนวณการใช้วัตถุดิบ
            ingredient_usage = defaultdict(float)
            
            for item in menu_usage:
                if item['ingredients']:
                    try:
                        ingredients = json.loads(item['ingredients'])
                        for ingredient in ingredients:
                            ingredient_name = ingredient.get('name', '')
                            quantity_per_item = ingredient.get('quantity', 0)
                            total_needed = quantity_per_item * item['total_sold']
                            ingredient_usage[ingredient_name] += total_needed
                    except (json.JSONDecodeError, KeyError):
                        continue
            
            # ทำนายความต้องการสำหรับวันข้างหน้า
            daily_average = {ingredient: usage / 7 for ingredient, usage in ingredient_usage.items()}
            predicted_needs = {ingredient: avg * days_ahead for ingredient, avg in daily_average.items()}
            
            # ตรวจสอบสต็อกปัจจุบัน
            cursor.execute("SELECT name, current_stock, unit FROM stock_items")
            current_stock = {row['name']: {'stock': row['current_stock'], 'unit': row['unit']} for row in cursor.fetchall()}
            
            # สร้างคำแนะนำ
            recommendations = []
            for ingredient, predicted_need in predicted_needs.items():
                current = current_stock.get(ingredient, {'stock': 0, 'unit': 'unit'})
                if current['stock'] < predicted_need:
                    shortage = predicted_need - current['stock']
                    recommendations.append({
                        'ingredient': ingredient,
                        'current_stock': current['stock'],
                        'predicted_need': predicted_need,
                        'shortage': shortage,
                        'unit': current['unit'],
                        'recommendation': f"ควรสั่ง {ingredient} เพิ่ม {shortage:.2f} {current['unit']}"
                    })
            
            conn.close()
            
            return {
                'prediction_date': (date.today() + timedelta(days=days_ahead)).isoformat(),
                'analysis_period': f"{start_date.isoformat()} to {date.today().isoformat()}",
                'ingredient_usage_history': dict(ingredient_usage),
                'daily_average_usage': daily_average,
                'predicted_needs': predicted_needs,
                'current_stock': current_stock,
                'recommendations': recommendations,
                'total_ingredients_analyzed': len(ingredient_usage)
            }
            
        except Exception as e:
            self.logger.error(f"Error predicting ingredient needs: {e}")
            return None
    
    def generate_ai_insights(self):
        """สร้าง AI insights รวม"""
        try:
            daily_analysis = self.analyze_daily_sales()
            menu_analysis = self.analyze_menu_performance()
            ingredient_prediction = self.predict_ingredient_needs()
            
            insights = {
                'generated_at': datetime.now().isoformat(),
                'daily_sales': daily_analysis,
                'menu_performance': menu_analysis,
                'ingredient_predictions': ingredient_prediction,
                'summary_insights': []
            }
            
            # สร้าง summary insights
            if daily_analysis:
                if daily_analysis['revenue_change_percent'] > 10:
                    insights['summary_insights'].append("📈 ยอดขายวันนี้เพิ่มขึ้นมากกว่า 10% เมื่อเทียบกับเมื่อวาน")
                elif daily_analysis['revenue_change_percent'] < -10:
                    insights['summary_insights'].append("📉 ยอดขายวันนี้ลดลงมากกว่า 10% เมื่อเทียบกับเมื่อวาน")
                
                if daily_analysis['peak_hour']:
                    insights['summary_insights'].append(f"⏰ ช่วงเวลาที่มีลูกค้ามากที่สุดคือ {daily_analysis['peak_hour']}:00 น.")
            
            if menu_analysis and menu_analysis['top_sellers']:
                top_seller = menu_analysis['top_sellers'][0]
                insights['summary_insights'].append(f"🏆 เมนูขายดีที่สุดคือ '{top_seller['menu_name']}' ขายได้ {top_seller['total_sold']} รายการ")
            
            if ingredient_prediction and ingredient_prediction['recommendations']:
                urgent_recommendations = [r for r in ingredient_prediction['recommendations'] if r['shortage'] > r['current_stock']]
                if urgent_recommendations:
                    insights['summary_insights'].append(f"⚠️ มีวัตถุดิบ {len(urgent_recommendations)} รายการที่ต้องสั่งเพิ่มด่วน")
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating AI insights: {e}")
            return None

