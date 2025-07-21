import sqlite3
import json
from datetime import datetime, timedelta
import hashlib

def create_complete_database(db_path='pos_database.db'):
    """สร้างฐานข้อมูลที่สมบูรณ์พร้อมข้อมูลตัวอย่าง"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # สร้างตารางผู้ใช้
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT,
        role TEXT DEFAULT 'staff',
        is_active BOOLEAN DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_login TEXT
    )
''')
    
    # สร้างตารางร้าน
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            logo_url TEXT,
            phone TEXT,
            address TEXT,
            pos_type TEXT DEFAULT 'restaurant',
            package_type TEXT DEFAULT 'basic',
            is_open BOOLEAN DEFAULT 0,
            last_opened_at TEXT,
            last_closed_at TEXT,
            auto_closed BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # สร้างตารางหมวดหมู่เมนู
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            display_order INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES stores (id)
        )
    ''')
    
    # สร้างตารางเมนู
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER,
            category_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            cost REAL DEFAULT 0,
            image_url TEXT,
            is_available BOOLEAN DEFAULT 1,
            is_featured BOOLEAN DEFAULT 0,
            preparation_time INTEGER DEFAULT 15,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES stores (id),
            FOREIGN KEY (category_id) REFERENCES menu_categories (id)
        )
    ''')
    
    # สร้างตารางออร์เดอร์
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER,
            order_number TEXT UNIQUE,
            table_number TEXT,
            customer_name TEXT,
            customer_phone TEXT,
            status TEXT DEFAULT 'pending',
            payment_method TEXT DEFAULT 'cash',
            payment_status TEXT DEFAULT 'pending',
            subtotal REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            discount REAL DEFAULT 0,
            total REAL DEFAULT 0,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            FOREIGN KEY (store_id) REFERENCES stores (id)
        )
    ''')
    
    # สร้างตารางรายการในออร์เดอร์
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            menu_item_id INTEGER,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            customizations TEXT,
            notes TEXT,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (menu_item_id) REFERENCES menu_items (id)
        )
    ''')
    
    # สร้างตารางโฆษณา
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS advertisements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            image_url TEXT,
            display_duration INTEGER DEFAULT 5000,
            priority INTEGER DEFAULT 1,
            start_date TEXT,
            end_date TEXT,
            is_active BOOLEAN DEFAULT 1,
            display_count INTEGER DEFAULT 0,
            last_displayed_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES stores (id)
        )
    ''')
    
    # สร้างตารางการตั้งค่าการแสดงผล
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS display_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER UNIQUE,
            settings_data TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES stores (id)
        )
    ''')
    
    # สร้างตารางการตั้งค่าปิดร้านอัตโนมัติ
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auto_close_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER UNIQUE,
            close_time TEXT NOT NULL,
            enabled BOOLEAN DEFAULT 1,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES stores (id)
        )
    ''')
    
    # สร้างตารางสรุปยอดขายรายวัน
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER,
            date TEXT,
            summary_data TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES stores (id)
        )
    ''')
    
    # สร้างตารางโปรโมชั่น
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            discount_type TEXT DEFAULT 'percentage',
            discount_value REAL DEFAULT 0,
            min_order_amount REAL DEFAULT 0,
            start_date TEXT,
            end_date TEXT,
            is_active BOOLEAN DEFAULT 1,
            priority INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES stores (id)
        )
    ''')
    
    # สร้างตารางสต็อก
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER,
            name TEXT NOT NULL,
            unit TEXT DEFAULT 'ชิ้น',
            current_stock REAL DEFAULT 0,
            min_stock REAL DEFAULT 0,
            max_stock REAL DEFAULT 0,
            cost_per_unit REAL DEFAULT 0,
            supplier TEXT,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES stores (id)
        )
    ''')
    
    conn.commit()
    
    # เพิ่มข้อมูลตัวอย่าง
    insert_sample_data(cursor)
    
    conn.commit()
    conn.close()
    
    print("✅ สร้างฐานข้อมูลสมบูรณ์เรียบร้อยแล้ว")

def insert_sample_data(cursor):
    """เพิ่มข้อมูลตัวอย่าง"""
    
    # เพิ่มผู้ใช้ตัวอย่าง
    password_hash = hashlib.sha256("admin123".encode()).hexdigest()
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, email, password_hash, full_name, role)
        VALUES (?, ?, ?, ?, ?)
    ''', ("admin", "admin@goodsalepos.com", password_hash, "ผู้ดูแลระบบ", "admin"))
    
    # เพิ่มร้านตัวอย่าง
    cursor.execute('''
        INSERT OR IGNORE INTO stores (id, name, description, phone, address, pos_type, package_type, is_open)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (1, "ร้านกาแฟดีดี", "ร้านกาแฟและเบเกอรี่", "02-123-4567", "กรุงเทพมหานคร", "coffee", "premium", 1))
    
    # เพิ่มหมวดหมู่เมนู
    categories = [
        (1, 1, "เครื่องดื่มร้อน", "กาแฟและชาร้อน", 1),
        (2, 1, "เครื่องดื่มเย็น", "กาแฟเย็นและน้ำผลไม้", 2),
        (3, 1, "เบเกอรี่", "ขนมปังและเค้ก", 3),
        (4, 1, "อาหารว่าง", "ขนมและของทานเล่น", 4)
    ]
    
    for cat in categories:
        cursor.execute('''
            INSERT OR IGNORE INTO menu_categories (id, store_id, name, description, display_order)
            VALUES (?, ?, ?, ?, ?)
        ''', cat)
    
    # เพิ่มเมนูตัวอย่าง
    menu_items = [
        (1, 1, 1, "เอสเปรสโซ", "กาแฟเข้มข้นแท้", 45.0, 15.0, None, 1, 0, 5),
        (2, 1, 1, "อเมริกาโน", "เอสเปรสโซผสมน้ำร้อน", 55.0, 18.0, None, 1, 1, 5),
        (3, 1, 1, "คาปูชิโน", "เอสเปรสโซผสมนมร้อน", 65.0, 22.0, None, 1, 1, 8),
        (4, 1, 1, "ลาเต้", "เอสเปรสโซผสมนมร้อนและฟองนม", 70.0, 25.0, None, 1, 1, 8),
        (5, 1, 2, "ไอซ์อเมริกาโน", "เอสเปรสโซผสมน้ำเย็น", 60.0, 20.0, None, 1, 1, 5),
        (6, 1, 2, "ไอซ์ลาเต้", "เอสเปรสโซผสมนมเย็น", 75.0, 27.0, None, 1, 1, 8),
        (7, 1, 2, "ฟราปเป้", "กาแฟปั่นน้ำแข็ง", 85.0, 30.0, None, 1, 1, 10),
        (8, 1, 3, "ครัวซองต์", "ขนมปังเนยสดฝรั่งเศส", 45.0, 20.0, None, 1, 0, 15),
        (9, 1, 3, "มัฟฟินบลูเบอร์รี่", "มัฟฟินผลไม้สด", 55.0, 25.0, None, 1, 1, 20),
        (10, 1, 4, "คุกกี้ช็อกโกแลต", "คุกกี้ช็อกโกแลตชิป", 35.0, 15.0, None, 1, 0, 10)
    ]
    
    for item in menu_items:
        cursor.execute('''
            INSERT OR IGNORE INTO menu_items 
            (id, store_id, category_id, name, description, price, cost, image_url, is_available, is_featured, preparation_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', item)
    
    # เพิ่มออร์เดอร์ตัวอย่าง
    base_date = datetime.now() - timedelta(days=7)
    
    for i in range(1, 21):  # สร้าง 20 ออร์เดอร์
        order_date = base_date + timedelta(days=i % 7, hours=i % 12, minutes=i * 15 % 60)
        order_number = f"ORD{order_date.strftime('%Y%m%d')}{i:03d}"
        
        # สุ่มสถานะ
        statuses = ['completed', 'completed', 'completed', 'cancelled']
        status = statuses[i % len(statuses)]
        
        # คำนวณยอดรวม
        subtotal = 50 + (i * 25) % 200
        tax = subtotal * 0.07
        total = subtotal + tax
        
        completed_at = order_date + timedelta(minutes=15) if status == 'completed' else None
        
        cursor.execute('''
            INSERT OR IGNORE INTO orders 
            (id, store_id, order_number, table_number, status, payment_method, payment_status, 
             subtotal, tax, total, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (i, 1, order_number, f"T{(i % 10) + 1}", status, 'cash', 'completed', 
              subtotal, tax, total, order_date.isoformat(), 
              completed_at.isoformat() if completed_at else None))
        
        # เพิ่มรายการในออร์เดอร์
        if status == 'completed':
            # เพิ่ม 1-3 รายการต่อออร์เดอร์
            num_items = (i % 3) + 1
            for j in range(num_items):
                menu_item_id = ((i + j) % 10) + 1
                quantity = (j % 2) + 1
                unit_price = 45 + (menu_item_id * 10)
                total_price = unit_price * quantity
                
                cursor.execute('''
                    INSERT OR IGNORE INTO order_items 
                    (order_id, menu_item_id, quantity, unit_price, total_price)
                    VALUES (?, ?, ?, ?, ?)
                ''', (i, menu_item_id, quantity, unit_price, total_price))
    
    # เพิ่มโฆษณาตัวอย่าง
    advertisements = [
        (1, "🎉 โปรโมชั่นพิเศษ!", "ซื้อกาแฟ 2 แก้ว ฟรี 1 แก้ว ทุกวันจันทร์-ศุกร์", 8000, 1, None, None),
        (1, "☕ เมนูใหม่มาแล้ว!", "ลองชิมกาแฟพรีเมียมคั่วใหม่ รสชาติเข้มข้น หอมกรุ่น", 6000, 2, None, None),
        (1, "🍰 เบเกอรี่สดใหม่", "ขนมปังและเค้กอบสดใหม่ทุกวัน เริ่มต้น 35 บาท", 7000, 3, None, None)
    ]
    
    for ad in advertisements:
        cursor.execute('''
            INSERT OR IGNORE INTO advertisements 
            (store_id, title, content, display_duration, priority, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ad)
    
    # เพิ่มโปรโมชั่นตัวอย่าง
    today = datetime.now().date()
    next_month = today + timedelta(days=30)
    
    promotions = [
        (1, "Happy Hour", "ลด 20% เครื่องดื่มทุกชนิด 14:00-16:00", "percentage", 20.0, 0, 
         today.isoformat(), next_month.isoformat(), 1, 1),
        (1, "ซื้อครบ 200 ลด 30", "ซื้อครับ 200 บาท ลดทันที 30 บาท", "fixed", 30.0, 200.0,
         today.isoformat(), next_month.isoformat(), 1, 2)
    ]
    
    for promo in promotions:
        cursor.execute('''
            INSERT OR IGNORE INTO promotions 
            (store_id, title, description, discount_type, discount_value, min_order_amount,
             start_date, end_date, is_active, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', promo)
    
    # เพิ่มสต็อกตัวอย่าง
    stock_items = [
        (1, "เมล็ดกาแฟอาราบิก้า", "กิโลกรัม", 50.0, 10.0, 100.0, 450.0, "บริษัท กาแฟดี จำกัด"),
        (1, "นมสด", "ลิตร", 20.0, 5.0, 50.0, 35.0, "โคนม"),
        (1, "น้ำตาล", "กิโลกรัม", 15.0, 3.0, 30.0, 25.0, "ร้านขายของชำ"),
        (1, "แป้งสาลี", "กิโลกรัม", 8.0, 2.0, 20.0, 40.0, "ร้านขายของชำ"),
        (1, "ไข่ไก่", "ฟอง", 120.0, 30.0, 200.0, 4.5, "ฟาร์มไก่"),
    ]
    
    for stock in stock_items:
        cursor.execute('''
            INSERT OR IGNORE INTO stock_items 
            (store_id, name, unit, current_stock, min_stock, max_stock, cost_per_unit, supplier)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', stock)
    
    print("✅ เพิ่มข้อมูลตัวอย่างเรียบร้อยแล้ว")

if __name__ == "__main__":
    create_complete_database()
