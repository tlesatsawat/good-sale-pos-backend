from flask import Blueprint, request, jsonify
import logging
from datetime import datetime, date, timedelta
from ai_analysis import AIAnalysisEngine

ai_bp = Blueprint('ai_recommendations', __name__)
logger = logging.getLogger(__name__)

@ai_bp.route('/daily-summary', methods=['GET'])
def get_daily_summary():
    """ดึงสรุปยอดขายรายวัน"""
    try:
        target_date_str = request.args.get('date')
        target_date = date.fromisoformat(target_date_str) if target_date_str else date.today()
        
        ai_engine = AIAnalysisEngine()
        summary = ai_engine.analyze_daily_sales(target_date)
        
        if summary:
            return jsonify({
                'success': True,
                'data': summary
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถวิเคราะห์ข้อมูลได้'
            }), 500
            
    except Exception as e:
        logger.error(f"Error getting daily summary: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการดึงข้อมูล'
        }), 500

@ai_bp.route('/menu-analysis', methods=['GET'])
def get_menu_analysis():
    """วิเคราะห์เมนูขายดี"""
    try:
        days = int(request.args.get('days', 7))
        
        ai_engine = AIAnalysisEngine()
        analysis = ai_engine.analyze_menu_performance(days)
        
        if analysis:
            return jsonify({
                'success': True,
                'data': analysis
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถวิเคราะห์เมนูได้'
            }), 500
            
    except Exception as e:
        logger.error(f"Error getting menu analysis: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการวิเคราะห์เมนู'
        }), 500

@ai_bp.route('/ingredient-recommendations', methods=['GET'])
def get_ingredient_recommendations():
    """แนะนำการสั่งวัตถุดิบ"""
    try:
        days_ahead = int(request.args.get('days_ahead', 1))
        
        ai_engine = AIAnalysisEngine()
        recommendations = ai_engine.predict_ingredient_needs(days_ahead)
        
        if recommendations:
            return jsonify({
                'success': True,
                'data': recommendations
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถสร้างคำแนะนำได้'
            }), 500
            
    except Exception as e:
        logger.error(f"Error getting ingredient recommendations: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการสร้างคำแนะนำ'
        }), 500

@ai_bp.route('/insights', methods=['GET'])
def get_ai_insights():
    """ดึง AI insights รวม"""
    try:
        ai_engine = AIAnalysisEngine()
        insights = ai_engine.generate_ai_insights()
        
        if insights:
            return jsonify({
                'success': True,
                'data': insights
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถสร้าง insights ได้'
            }), 500
            
    except Exception as e:
        logger.error(f"Error getting AI insights: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการสร้าง insights'
        }), 500

@ai_bp.route('/trend-analysis', methods=['GET'])
def get_trend_analysis():
    """วิเคราะห์แนวโน้มการขาย"""
    try:
        days = int(request.args.get('days', 30))
        
        ai_engine = AIAnalysisEngine()
        
        # วิเคราะห์แนวโน้มยอดขายรายวัน
        daily_trends = []
        for i in range(days):
            target_date = date.today() - timedelta(days=i)
            daily_data = ai_engine.analyze_daily_sales(target_date)
            if daily_data:
                daily_trends.append({
                    'date': daily_data['date'],
                    'revenue': daily_data['total_revenue'],
                    'orders': daily_data['total_orders']
                })
        
        # คำนวณแนวโน้ม
        if len(daily_trends) >= 7:
            recent_week = daily_trends[:7]
            previous_week = daily_trends[7:14] if len(daily_trends) >= 14 else []
            
            recent_avg_revenue = sum(d['revenue'] for d in recent_week) / len(recent_week)
            previous_avg_revenue = sum(d['revenue'] for d in previous_week) / len(previous_week) if previous_week else recent_avg_revenue
            
            trend_percentage = ((recent_avg_revenue - previous_avg_revenue) / previous_avg_revenue * 100) if previous_avg_revenue > 0 else 0
            
            trend_analysis = {
                'period': f"{days} days",
                'daily_data': daily_trends,
                'recent_week_avg_revenue': recent_avg_revenue,
                'previous_week_avg_revenue': previous_avg_revenue,
                'trend_percentage': round(trend_percentage, 2),
                'trend_direction': 'เพิ่มขึ้น' if trend_percentage > 0 else 'ลดลง' if trend_percentage < 0 else 'คงที่'
            }
        else:
            trend_analysis = {
                'period': f"{days} days",
                'daily_data': daily_trends,
                'message': 'ข้อมูลไม่เพียงพอสำหรับการวิเคราะห์แนวโน้ม'
            }
        
        return jsonify({
            'success': True,
            'data': trend_analysis
        })
        
    except Exception as e:
        logger.error(f"Error getting trend analysis: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการวิเคราะห์แนวโน้ม'
        }), 500

@ai_bp.route('/store-close-summary', methods=['POST'])
def get_store_close_summary():
    """สรุปข้อมูลเมื่อปิดร้าน (สำหรับ Modal)"""
    try:
        data = request.get_json()
        store_id = data.get('store_id')
        close_date = data.get('date', date.today().isoformat())
        
        ai_engine = AIAnalysisEngine()
        
        # ดึงข้อมูลสรุปวันนี้
        daily_summary = ai_engine.analyze_daily_sales(date.fromisoformat(close_date))
        
        # ดึงข้อมูลเมนูขายดี
        menu_analysis = ai_engine.analyze_menu_performance(1)  # วันนี้เท่านั้น
        
        # ดึงคำแนะนำวัตถุดิบสำหรับพรุ่งนี้
        ingredient_recommendations = ai_engine.predict_ingredient_needs(1)
        
        # สร้างข้อความแนะนำ
        recommendations_text = []
        if ingredient_recommendations and ingredient_recommendations['recommendations']:
            for rec in ingredient_recommendations['recommendations'][:5]:  # แสดงแค่ 5 อันดับแรก
                recommendations_text.append(rec['recommendation'])
        
        summary = {
            'store_id': store_id,
            'close_date': close_date,
            'daily_summary': daily_summary,
            'top_menu_items': menu_analysis['top_sellers'][:5] if menu_analysis else [],
            'ingredient_recommendations': recommendations_text,
            'ai_message': _generate_closing_message(daily_summary, menu_analysis),
            'generated_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        logger.error(f"Error getting store close summary: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการสร้างสรุป'
        }), 500

def _generate_closing_message(daily_summary, menu_analysis):
    """สร้างข้อความ AI สำหรับการปิดร้าน"""
    messages = []
    
    if daily_summary:
        revenue = daily_summary.get('total_revenue', 0)
        orders = daily_summary.get('total_orders', 0)
        change = daily_summary.get('revenue_change_percent', 0)
        
        if revenue > 0:
            messages.append(f"วันนี้ยอดขายรวม {revenue:,.2f} บาท จากออร์เดอร์ทั้งหมด {orders} รายการ")
            
            if change > 5:
                messages.append(f"ยอดขายเพิ่มขึ้น {change:.1f}% เมื่อเทียบกับเมื่อวาน 📈")
            elif change < -5:
                messages.append(f"ยอดขายลดลง {abs(change):.1f}% เมื่อเทียบกับเมื่อวาน 📉")
            else:
                messages.append("ยอดขายคงที่เมื่อเทียบกับเมื่อวาน")
    
    if menu_analysis and menu_analysis.get('top_sellers'):
        top_item = menu_analysis['top_sellers'][0]
        messages.append(f"เมนูขายดีที่สุดวันนี้คือ '{top_item['menu_name']}' ขายได้ {top_item['total_sold']} รายการ 🏆")
    
    messages.append("ขอบคุณสำหรับการทำงานหนักวันนี้! พรุ่งนี้จะเป็นวันที่ดีกว่านี้ 💪")
    
    return " ".join(messages)

