import sqlite3
import logging
from datetime import datetime

def update_database_schema():
    """Update database schema for new features"""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        conn = sqlite3.connect('pos_database.db')
        cursor = conn.cursor()
        
        logger.info("Starting database schema update...")
        
        # Create stock_items table for advanced inventory management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                barcode TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                unit TEXT NOT NULL,
                cost_price REAL NOT NULL,
                selling_price REAL NOT NULL,
                min_stock_level INTEGER DEFAULT 10,
                max_stock_level INTEGER DEFAULT 100,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        ''')
        
        # Create stock_movements table for tracking inventory changes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_item_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL CHECK (movement_type IN ('in', 'out', 'adjustment')),
                quantity_change INTEGER NOT NULL,
                reason TEXT NOT NULL,
                reference_id TEXT,
                lot_number TEXT,
                expiry_date TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (stock_item_id) REFERENCES stock_items (id)
            )
        ''')
        
        # Create loyalty_members table for loyalty program
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS loyalty_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                date_of_birth TEXT,
                points_balance INTEGER DEFAULT 0,
                tier TEXT DEFAULT 'Bronze' CHECK (tier IN ('Bronze', 'Silver', 'Gold', 'Platinum')),
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        ''')
        
        # Create points_transactions table for tracking points
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS points_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL CHECK (transaction_type IN ('earn', 'redeem')),
                points INTEGER NOT NULL,
                description TEXT NOT NULL,
                order_id INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (member_id) REFERENCES loyalty_members (id),
                FOREIGN KEY (order_id) REFERENCES orders (id)
            )
        ''')
        
        # Create ui_customizations table for UI/UX customization
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ui_customizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id INTEGER NOT NULL,
                customization_type TEXT NOT NULL,
                settings TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (store_id) REFERENCES stores (id)
            )
        ''')
        
        # Create cache_entries table for application-level caching
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE NOT NULL,
                cache_value TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Add indexes for better performance
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_stock_items_barcode ON stock_items(barcode)',
            'CREATE INDEX IF NOT EXISTS idx_stock_movements_item_id ON stock_movements(stock_item_id)',
            'CREATE INDEX IF NOT EXISTS idx_stock_movements_created_at ON stock_movements(created_at)',
            'CREATE INDEX IF NOT EXISTS idx_loyalty_members_phone ON loyalty_members(phone)',
            'CREATE INDEX IF NOT EXISTS idx_loyalty_members_member_id ON loyalty_members(member_id)',
            'CREATE INDEX IF NOT EXISTS idx_points_transactions_member_id ON points_transactions(member_id)',
            'CREATE INDEX IF NOT EXISTS idx_points_transactions_created_at ON points_transactions(created_at)',
            'CREATE INDEX IF NOT EXISTS idx_ui_customizations_store_id ON ui_customizations(store_id)',
            'CREATE INDEX IF NOT EXISTS idx_cache_entries_expires_at ON cache_entries(expires_at)'
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        # Insert sample stock items for testing
        sample_stock_items = [
            ('กาแฟเอสเปรสโซ่', '8851234567890', 'เครื่องดื่ม', 'แก้ว', 15.00, 45.00, 20, 200),
            ('กาแฟลาเต้', '8851234567891', 'เครื่องดื่ม', 'แก้ว', 18.00, 55.00, 15, 150),
            ('ชาเขียว', '8851234567892', 'เครื่องดื่ม', 'แก้ว', 12.00, 35.00, 25, 250),
            ('ขนมปังโครซองต์', '8851234567893', 'ขนม', 'ชิ้น', 8.00, 25.00, 30, 100),
            ('คุกกี้ช็อกโกแลต', '8851234567894', 'ขนม', 'ชิ้น', 5.00, 15.00, 50, 200),
        ]
        
        for item in sample_stock_items:
            cursor.execute('''
                INSERT OR IGNORE INTO stock_items (
                    name, barcode, category, unit, cost_price, selling_price,
                    min_stock_level, max_stock_level, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (*item, datetime.now().isoformat()))
        
        # Insert initial stock for sample items
        cursor.execute('SELECT id FROM stock_items')
        stock_items = cursor.fetchall()
        
        for item in stock_items:
            # Add initial stock (100 units for each item)
            cursor.execute('''
                INSERT OR IGNORE INTO stock_movements (
                    stock_item_id, movement_type, quantity_change, reason, created_at
                ) VALUES (?, ?, ?, ?, ?)
            ''', (item[0], 'in', 100, 'Initial stock', datetime.now().isoformat()))
        
        # Insert sample loyalty member for testing
        cursor.execute('''
            INSERT OR IGNORE INTO loyalty_members (
                member_id, name, phone, email, points_balance, tier, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('DEMO0001', 'ลูกค้าทดสอบ', '0812345678', 'demo@example.com', 500, 'Silver', datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        logger.info("Database schema update completed successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating database schema: {str(e)}")
        return False

if __name__ == "__main__":
    success = update_database_schema()
    if success:
        print("✅ Database schema updated successfully!")
    else:
        print("❌ Failed to update database schema!")

