from flask import Blueprint, request, jsonify, session

from datetime import datetime, date, timedelta
import random

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/stores/<int:store_id>/reports/daily-sales', methods=['GET'])
def get_daily_sales(store_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        # Get date parameter or use today
        date_str = request.args.get('date')
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            target_date = date.today()
        
        # Get orders for the specified date
        orders = Order.query.filter(
            Order.store_id == store_id,
            func.date(Order.order_time) == target_date,
            Order.status == 'completed'
        ).all()
        
        # Calculate metrics
        total_sales = sum(float(order.total_amount) for order in orders)
        total_orders = len(orders)
        average_order_value = total_sales / total_orders if total_orders > 0 else 0
        
        # Get hourly breakdown
        hourly_sales = {}
        for order in orders:
            hour = order.order_time.hour
            if hour not in hourly_sales:
                hourly_sales[hour] = {'sales': 0, 'orders': 0}
            hourly_sales[hour]['sales'] += float(order.total_amount)
            hourly_sales[hour]['orders'] += 1
        
        # Convert to list format
        hourly_breakdown = []
        for hour in range(24):
            hourly_breakdown.append({
                'hour': hour,
                'sales': hourly_sales.get(hour, {}).get('sales', 0),
                'orders': hourly_sales.get(hour, {}).get('orders', 0)
            })
        
        return jsonify({
            'date': target_date.isoformat(),
            'total_sales': total_sales,
            'total_orders': total_orders,
            'average_order_value': round(average_order_value, 2),
            'hourly_breakdown': hourly_breakdown,
            'orders': [order.to_dict() for order in orders]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/stores/<int:store_id>/reports/best-selling-items', methods=['GET'])
def get_best_selling_items(store_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        # Get date range parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        limit = request.args.get('limit', 10, type=int)
        
        # Default to last 7 days if no dates provided
        if not start_date_str or not end_date_str:
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
        else:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Query best selling items
        best_selling_query = db.session.query(
            OrderItem.item_name,
            func.sum(OrderItem.quantity).label('total_quantity'),
            func.sum(OrderItem.price * OrderItem.quantity).label('total_revenue'),
            func.count(OrderItem.id).label('order_count')
        ).join(Order).filter(
            Order.store_id == store_id,
            func.date(Order.order_time).between(start_date, end_date),
            Order.status == 'completed'
        ).group_by(OrderItem.item_name).order_by(desc('total_quantity')).limit(limit)
        
        best_selling_items = []
        for item in best_selling_query.all():
            best_selling_items.append({
                'item_name': item.item_name,
                'total_quantity': item.total_quantity,
                'total_revenue': float(item.total_revenue),
                'order_count': item.order_count,
                'average_price': float(item.total_revenue) / item.total_quantity if item.total_quantity > 0 else 0
            })
        
        return jsonify({
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'best_selling_items': best_selling_items
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/stores/<int:store_id>/reports/sales-history', methods=['GET'])
def get_sales_history(store_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        # Get query parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = Order.query.filter_by(store_id=store_id, status='completed')
        
        # Apply date filters if provided
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                query = query.filter(func.date(Order.order_time) >= start_date)
            except ValueError:
                return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD'}), 400
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                query = query.filter(func.date(Order.order_time) <= end_date)
            except ValueError:
                return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD'}), 400
        
        # Paginate results
        orders = query.order_by(desc(Order.order_time)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'orders': [order.to_dict() for order in orders.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': orders.total,
                'pages': orders.pages,
                'has_next': orders.has_next,
                'has_prev': orders.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/stores/<int:store_id>/reports/ai-analysis', methods=['GET'])
def get_ai_analysis(store_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        # Get data for last 7 days
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        # Get orders for analysis
        orders = Order.query.filter(
            Order.store_id == store_id,
            func.date(Order.order_time).between(start_date, end_date),
            Order.status == 'completed'
        ).all()
        
        if not orders:
            return jsonify({
                'analysis': {
                    'insights': ['ยังไม่มีข้อมูลยอดขายเพียงพอสำหรับการวิเคราะห์'],
                    'recommendations': ['เริ่มต้นขายและสะสมข้อมูลเพื่อการวิเคราะห์ที่แม่นยำยิ่งขึ้น']
                }
            }), 200
        
        # Calculate metrics
        total_sales = sum(float(order.total_amount) for order in orders)
        total_orders = len(orders)
        avg_order_value = total_sales / total_orders
        
        # Get best selling items
        best_selling_query = db.session.query(
            OrderItem.item_name,
            func.sum(OrderItem.quantity).label('total_quantity')
        ).join(Order).filter(
            Order.store_id == store_id,
            func.date(Order.order_time).between(start_date, end_date),
            Order.status == 'completed'
        ).group_by(OrderItem.item_name).order_by(desc('total_quantity')).limit(3)
        
        best_items = [item.item_name for item in best_selling_query.all()]
        
        # Generate AI insights (simplified simulation)
        insights = []
        recommendations = []
        
        if total_orders > 0:
            insights.append(f"ยอดขายรวม 7 วันที่ผ่านมา: {total_sales:,.2f} บาท")
            insights.append(f"จำนวนออร์เดอร์ทั้งหมด: {total_orders} ออร์เดอร์")
            insights.append(f"ยอดขายเฉลี่ยต่อออร์เดอร์: {avg_order_value:.2f} บาท")
        
        if best_items:
            insights.append(f"เมนูขายดีอันดับ 1: {best_items[0]}")
            recommendations.append(f"แนะนำให้เตรียมวัตถุดิบสำหรับ '{best_items[0]}' เพิ่มขึ้น 20%")
        
        # Day of week analysis
        daily_sales = {}
        for order in orders:
            day_name = order.order_time.strftime('%A')
            if day_name not in daily_sales:
                daily_sales[day_name] = 0
            daily_sales[day_name] += float(order.total_amount)
        
        if daily_sales:
            best_day = max(daily_sales, key=daily_sales.get)
            insights.append(f"วันที่ขายดีที่สุด: {best_day}")
            recommendations.append(f"วัน{best_day}มียอดขายดี ควรเตรียมพร้อมเป็นพิเศษ")
        
        # Time-based recommendations
        current_hour = datetime.now().hour
        if 6 <= current_hour <= 10:
            recommendations.append("ช่วงเช้า: เตรียมเมนูอาหารเช้าและเครื่องดื่มร้อน")
        elif 11 <= current_hour <= 14:
            recommendations.append("ช่วงกลางวัน: เตรียมเมนูอาหารจานหลักและเครื่องดื่มเย็น")
        elif 17 <= current_hour <= 20:
            recommendations.append("ช่วงเย็น: เตรียมเมนูอาหารเย็นและของว่าง")
        
        # Stock recommendations based on POS type
        if store.pos_type == 'coffee':
            recommendations.append("ตรวจสอบสต็อกเมล็ดกาแฟ นม และน้ำตาลทุกวัน")
            recommendations.append("เตรียมแก้วและฝาพิเศษสำหรับช่วงเวลาเร่งด่วน")
        elif store.pos_type == 'restaurant':
            recommendations.append("วางแผนการสั่งซื้อวัตถุดิบล่วงหน้า 1-2 วัน")
            recommendations.append("เตรียมเมนูยอดนิยมในปริมาณที่เพียงพอ")
        
        return jsonify({
            'analysis_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'analysis': {
                'insights': insights,
                'recommendations': recommendations,
                'best_selling_items': best_items,
                'metrics': {
                    'total_sales': total_sales,
                    'total_orders': total_orders,
                    'average_order_value': round(avg_order_value, 2)
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/stores/<int:store_id>/reports/sales-trend', methods=['GET'])
def get_sales_trend(store_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        store = Store.query.filter_by(id=store_id, user_id=user_id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        # Get last 30 days of data
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        # Query daily sales
        daily_sales_query = db.session.query(
            func.date(Order.order_time).label('date'),
            func.sum(Order.total_amount).label('daily_sales'),
            func.count(Order.id).label('daily_orders')
        ).filter(
            Order.store_id == store_id,
            func.date(Order.order_time).between(start_date, end_date),
            Order.status == 'completed'
        ).group_by(func.date(Order.order_time)).order_by('date')
        
        daily_data = []
        for row in daily_sales_query.all():
            daily_data.append({
                'date': row.date.isoformat(),
                'sales': float(row.daily_sales),
                'orders': row.daily_orders
            })
        
        return jsonify({
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'daily_sales_trend': daily_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

