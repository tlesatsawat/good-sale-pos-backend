from flask import Blueprint, request, jsonify
import logging
from customer_display import customer_display_manager

customer_display_bp = Blueprint('customer_display', __name__)
logger = logging.getLogger(__name__)

@customer_display_bp.route('/content/<int:store_id>', methods=['GET'])
def get_display_content(store_id):
    """ดึงเนื้อหาสำหรับแสดงบนจอลูกค้า"""
    try:
        content = customer_display_manager.get_display_content(store_id)
        
        return jsonify({
            'success': True,
            'data': content
        })
        
    except Exception as e:
        logger.error(f"Error getting display content: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการดึงเนื้อหา'
        }), 500

@customer_display_bp.route('/advertisements', methods=['POST'])
def add_advertisement():
    """เพิ่มโฆษณาใหม่"""
    try:
        data = request.get_json()
        store_id = data.get('store_id', 1)
        
        required_fields = ['title', 'content', 'display_duration']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'ไม่พบข้อมูล {field}'
                }), 400
        
        success = customer_display_manager.add_advertisement(store_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'เพิ่มโฆษณาเรียบร้อยแล้ว'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถเพิ่มโฆษณาได้'
            }), 500
            
    except Exception as e:
        logger.error(f"Error adding advertisement: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการเพิ่มโฆษณา'
        }), 500

@customer_display_bp.route('/advertisements/<int:ad_id>', methods=['PUT'])
def update_advertisement(ad_id):
    """อัปเดตโฆษณา"""
    try:
        data = request.get_json()
        
        success = customer_display_manager.update_advertisement(ad_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'อัปเดตโฆษณาเรียบร้อยแล้ว'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถอัปเดตโฆษณาได้'
            }), 500
            
    except Exception as e:
        logger.error(f"Error updating advertisement: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการอัปเดตโฆษณา'
        }), 500

@customer_display_bp.route('/advertisements/<int:ad_id>', methods=['DELETE'])
def delete_advertisement(ad_id):
    """ลบโฆษณา"""
    try:
        success = customer_display_manager.delete_advertisement(ad_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'ลบโฆษณาเรียบร้อยแล้ว'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถลบโฆษณาได้'
            }), 500
            
    except Exception as e:
        logger.error(f"Error deleting advertisement: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการลบโฆษณา'
        }), 500

@customer_display_bp.route('/advertisements/<int:store_id>', methods=['GET'])
def get_advertisements(store_id):
    """ดึงรายการโฆษณา"""
    try:
        advertisements = customer_display_manager.get_active_advertisements(store_id)
        
        return jsonify({
            'success': True,
            'data': advertisements
        })
        
    except Exception as e:
        logger.error(f"Error getting advertisements: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการดึงรายการโฆษณา'
        }), 500

@customer_display_bp.route('/settings', methods=['POST'])
def set_display_settings():
    """ตั้งค่าการแสดงผล"""
    try:
        data = request.get_json()
        store_id = data.get('store_id', 1)
        settings = data.get('settings', {})
        
        success = customer_display_manager.set_display_settings(store_id, settings)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'ตั้งค่าการแสดงผลเรียบร้อยแล้ว'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถตั้งค่าการแสดงผลได้'
            }), 500
            
    except Exception as e:
        logger.error(f"Error setting display settings: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการตั้งค่า'
        }), 500

@customer_display_bp.route('/settings/<int:store_id>', methods=['GET'])
def get_display_settings(store_id):
    """ดึงการตั้งค่าการแสดงผล"""
    try:
        settings = customer_display_manager.get_display_settings(store_id)
        
        return jsonify({
            'success': True,
            'data': settings
        })
        
    except Exception as e:
        logger.error(f"Error getting display settings: {e}")
        return jsonify({
            'success': False,
            'message': 'เกิดข้อผิดพลาดในการดึงการตั้งค่า'
        }), 500

@customer_display_bp.route('/increment-display/<int:ad_id>', methods=['POST'])
def increment_display_count(ad_id):
    """เพิ่มจำนวนครั้งที่แสดงโฆษณา"""
    try:
        success = customer_display_manager.increment_display_count(ad_id)
        
        return jsonify({
            'success': success
        })
        
    except Exception as e:
        logger.error(f"Error incrementing display count: {e}")
        return jsonify({
            'success': False
        }), 500

@customer_display_bp.route('/display/<int:store_id>')
def customer_display_page(store_id):
    """หน้าจอลูกค้า"""
    try:
        # สร้างหน้าเว็บสำหรับจอลูกค้า
        html_content = f"""
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GOOD SALE POS - Customer Display</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            overflow: hidden;
            height: 100vh;
        }}
        
        .container {{
            display: grid;
            grid-template-rows: auto 1fr auto;
            height: 100vh;
            padding: 20px;
            gap: 20px;
        }}
        
        .header {{
            text-align: center;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}
        
        .store-name {{
            font-size: 3rem;
            font-weight: bold;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }}
        
        .store-description {{
            font-size: 1.2rem;
            opacity: 0.9;
        }}
        
        .main-content {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            overflow: hidden;
        }}
        
        .content-area {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            overflow: hidden;
        }}
        
        .sidebar {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        
        .sidebar-section {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}
        
        .section-title {{
            font-size: 1.5rem;
            font-weight: bold;
            margin-bottom: 15px;
            color: #fff;
        }}
        
        .advertisement {{
            text-align: center;
            animation: fadeInOut 8s infinite;
        }}
        
        .ad-title {{
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 15px;
            color: #ffd700;
        }}
        
        .ad-content {{
            font-size: 1.2rem;
            line-height: 1.6;
        }}
        
        .menu-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        
        .menu-item {{
            background: rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            transition: transform 0.3s ease;
        }}
        
        .menu-item:hover {{
            transform: scale(1.05);
        }}
        
        .menu-name {{
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .menu-price {{
            color: #ffd700;
            font-size: 1.1rem;
        }}
        
        .queue-info {{
            text-align: center;
        }}
        
        .queue-number {{
            font-size: 3rem;
            font-weight: bold;
            color: #ffd700;
            margin-bottom: 10px;
        }}
        
        .queue-text {{
            font-size: 1.1rem;
        }}
        
        .promotion {{
            background: linear-gradient(45deg, #ff6b6b, #ffd93d);
            color: #333;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            font-weight: bold;
            text-align: center;
        }}
        
        .footer {{
            text-align: center;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 15px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}
        
        .current-time {{
            font-size: 1.5rem;
            font-weight: bold;
        }}
        
        @keyframes fadeInOut {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
        }}
        
        @keyframes slideIn {{
            from {{ transform: translateX(-100%); }}
            to {{ transform: translateX(0); }}
        }}
        
        .slide-in {{
            animation: slideIn 0.5s ease-out;
        }}
        
        .loading {{
            display: flex;
            justify-content: center;
            align-items: center;
            height: 200px;
            font-size: 1.2rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="store-name" id="storeName">GOOD SALE POS</div>
            <div class="store-description" id="storeDescription">ยินดีต้อนรับสู่ร้านของเรา</div>
        </div>
        
        <div class="main-content">
            <div class="content-area">
                <div id="advertisementArea" class="advertisement">
                    <div class="loading">กำลังโหลดโฆษณา...</div>
                </div>
                
                <div id="featuredMenuArea" style="display: none;">
                    <div class="section-title">🌟 เมนูแนะนำ</div>
                    <div class="menu-grid" id="menuGrid"></div>
                </div>
            </div>
            
            <div class="sidebar">
                <div class="sidebar-section">
                    <div class="section-title">📋 คิวปัจจุบัน</div>
                    <div class="queue-info">
                        <div class="queue-number" id="queueNumber">0</div>
                        <div class="queue-text">รายการรอ</div>
                        <div class="queue-text">เวลารอประมาณ <span id="waitTime">15</span> นาที</div>
                    </div>
                </div>
                
                <div class="sidebar-section" id="promotionArea" style="display: none;">
                    <div class="section-title">🎉 โปรโมชั่น</div>
                    <div id="promotionList"></div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <div class="current-time" id="currentTime"></div>
        </div>
    </div>

    <script>
        const storeId = {store_id};
        let currentAdIndex = 0;
        let advertisements = [];
        let featuredMenu = [];
        let promotions = [];
        let displaySettings = {{}};
        
        // อัปเดตเวลา
        function updateTime() {{
            const now = new Date();
            const timeString = now.toLocaleString('th-TH', {{
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            }});
            document.getElementById('currentTime').textContent = timeString;
        }}
        
        // โหลดข้อมูลจาก API
        async function loadDisplayContent() {{
            try {{
                const response = await fetch(`/api/customer-display/content/${{storeId}}`);
                const data = await response.json();
                
                if (data.success) {{
                    const content = data.data;
                    
                    // อัปเดตข้อมูลร้าน
                    if (content.store_info) {{
                        document.getElementById('storeName').textContent = content.store_info.name || 'GOOD SALE POS';
                        document.getElementById('storeDescription').textContent = content.store_info.description || 'ยินดีต้อนรับสู่ร้านของเรา';
                    }}
                    
                    // อัปเดตโฆษณา
                    if (content.advertisements) {{
                        advertisements = content.advertisements;
                        if (advertisements.length > 0) {{
                            showAdvertisements();
                        }} else {{
                            showFeaturedMenu();
                        }}
                    }}
                    
                    // อัปเดตเมนูแนะนำ
                    if (content.featured_menu) {{
                        featuredMenu = content.featured_menu;
                        updateFeaturedMenu();
                    }}
                    
                    // อัปเดตโปรโมชั่น
                    if (content.promotions && content.promotions.length > 0) {{
                        promotions = content.promotions;
                        updatePromotions();
                    }}
                    
                    // อัปเดตข้อมูลคิว
                    if (content.queue_info) {{
                        document.getElementById('queueNumber').textContent = content.queue_info.pending_orders || 0;
                        document.getElementById('waitTime').textContent = content.queue_info.estimated_wait_minutes || 15;
                    }}
                    
                    // อัปเดตการตั้งค่า
                    if (content.settings) {{
                        displaySettings = content.settings;
                        applyDisplaySettings();
                    }}
                }}
            }} catch (error) {{
                console.error('Error loading display content:', error);
            }}
        }}
        
        // แสดงโฆษณา
        function showAdvertisements() {{
            if (advertisements.length === 0) {{
                showFeaturedMenu();
                return;
            }}
            
            const adArea = document.getElementById('advertisementArea');
            const featuredArea = document.getElementById('featuredMenuArea');
            
            adArea.style.display = 'block';
            featuredArea.style.display = 'none';
            
            function displayNextAd() {{
                const ad = advertisements[currentAdIndex];
                
                adArea.innerHTML = `
                    <div class="ad-title">${{ad.title}}</div>
                    <div class="ad-content">${{ad.content}}</div>
                    ${{ad.image_url ? `<img src="${{ad.image_url}}" style="max-width: 100%; margin-top: 20px; border-radius: 10px;">` : ''}}
                `;
                
                // เพิ่มจำนวนครั้งที่แสดง
                fetch(`/api/customer-display/increment-display/${{ad.id}}`, {{ method: 'POST' }});
                
                currentAdIndex = (currentAdIndex + 1) % advertisements.length;
                
                // ตั้งเวลาสำหรับโฆษณาถัดไป
                const duration = ad.display_duration || displaySettings.advertisement_interval || 5000;
                setTimeout(displayNextAd, duration);
            }}
            
            displayNextAd();
        }}
        
        // แสดงเมนูแนะนำ
        function showFeaturedMenu() {{
            const adArea = document.getElementById('advertisementArea');
            const featuredArea = document.getElementById('featuredMenuArea');
            
            adArea.style.display = 'none';
            featuredArea.style.display = 'block';
        }}
        
        // อัปเดตเมนูแนะนำ
        function updateFeaturedMenu() {{
            const menuGrid = document.getElementById('menuGrid');
            
            menuGrid.innerHTML = featuredMenu.map(item => `
                <div class="menu-item slide-in">
                    <div class="menu-name">${{item.name}}</div>
                    <div class="menu-price">${{item.price.toLocaleString()}} บาท</div>
                </div>
            `).join('');
        }}
        
        // อัปเดตโปรโมชั่น
        function updatePromotions() {{
            const promotionArea = document.getElementById('promotionArea');
            const promotionList = document.getElementById('promotionList');
            
            if (promotions.length > 0) {{
                promotionArea.style.display = 'block';
                promotionList.innerHTML = promotions.map(promo => `
                    <div class="promotion">
                        ${{promo.title}}
                    </div>
                `).join('');
            }} else {{
                promotionArea.style.display = 'none';
            }}
        }}
        
        // ใช้การตั้งค่าการแสดงผล
        function applyDisplaySettings() {{
            if (displaySettings.background_color) {{
                document.body.style.background = displaySettings.background_color;
            }}
            
            if (displaySettings.text_color) {{
                document.body.style.color = displaySettings.text_color;
            }}
        }}
        
        // เริ่มต้น
        updateTime();
        setInterval(updateTime, 1000);
        
        loadDisplayContent();
        setInterval(loadDisplayContent, 30000); // อัปเดตทุก 30 วินาที
    </script>
</body>
</html>
        """
        
        return html_content
        
    except Exception as e:
        logger.error(f"Error rendering customer display page: {e}")
        return f"Error: {str(e)}", 500

