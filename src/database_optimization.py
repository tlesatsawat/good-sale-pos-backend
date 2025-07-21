import sqlite3
import logging
from datetime import datetime

class DatabaseOptimizer:
    def __init__(self, db_path='pos_database.db'):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def create_indexes(self):
        """Create database indexes for better performance"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Indexes for frequently queried columns
            indexes = [
                # Users table
                "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
                "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
                "CREATE INDEX IF NOT EXISTS idx_users_pos_type ON users(pos_type)",
                
                # Stores table
                "CREATE INDEX IF NOT EXISTS idx_stores_user_id ON stores(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_stores_is_open ON stores(is_open)",
                
                # Orders table
                "CREATE INDEX IF NOT EXISTS idx_orders_store_id ON orders(store_id)",
                "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
                "CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_orders_store_status ON orders(store_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_orders_store_date ON orders(store_id, DATE(created_at))",
                
                # Order Items table
                "CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id)",
                "CREATE INDEX IF NOT EXISTS idx_order_items_menu_item_id ON order_items(menu_item_id)",
                
                # Menu Items table
                "CREATE INDEX IF NOT EXISTS idx_menu_items_store_id ON menu_items(store_id)",
                "CREATE INDEX IF NOT EXISTS idx_menu_items_category ON menu_items(category)",
                "CREATE INDEX IF NOT EXISTS idx_menu_items_available ON menu_items(is_available)",
                
                # Stock Items table
                "CREATE INDEX IF NOT EXISTS idx_stock_items_store_id ON stock_items(store_id)",
                "CREATE INDEX IF NOT EXISTS idx_stock_items_barcode ON stock_items(barcode)",
                "CREATE INDEX IF NOT EXISTS idx_stock_items_low_stock ON stock_items(current_stock, min_stock_level)",
                
                # Stock Movements table
                "CREATE INDEX IF NOT EXISTS idx_stock_movements_item_id ON stock_movements(stock_item_id)",
                "CREATE INDEX IF NOT EXISTS idx_stock_movements_date ON stock_movements(movement_date)",
                "CREATE INDEX IF NOT EXISTS idx_stock_movements_type ON stock_movements(movement_type)",
                
                # Loyalty Members table
                "CREATE INDEX IF NOT EXISTS idx_loyalty_members_store_id ON loyalty_members(store_id)",
                "CREATE INDEX IF NOT EXISTS idx_loyalty_members_phone ON loyalty_members(phone_number)",
                "CREATE INDEX IF NOT EXISTS idx_loyalty_members_member_id ON loyalty_members(member_id)",
                
                # Loyalty Points table
                "CREATE INDEX IF NOT EXISTS idx_loyalty_points_member_id ON loyalty_points(member_id)",
                "CREATE INDEX IF NOT EXISTS idx_loyalty_points_date ON loyalty_points(transaction_date)",
                "CREATE INDEX IF NOT EXISTS idx_loyalty_points_type ON loyalty_points(transaction_type)",
                
                # Cache Entries table
                "CREATE INDEX IF NOT EXISTS idx_cache_entries_key ON cache_entries(cache_key)",
                "CREATE INDEX IF NOT EXISTS idx_cache_entries_expires ON cache_entries(expires_at)",
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
                self.logger.info(f"Created index: {index_sql.split('idx_')[1].split(' ')[0] if 'idx_' in index_sql else 'unknown'}")
            
            conn.commit()
            conn.close()
            
            self.logger.info("Database indexes created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating indexes: {str(e)}")
            return False
    
    def analyze_database(self):
        """Analyze database to update statistics for query optimizer"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Run ANALYZE to update database statistics
            cursor.execute("ANALYZE")
            
            conn.commit()
            conn.close()
            
            self.logger.info("Database analysis completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Error analyzing database: {str(e)}")
            return False
    
    def vacuum_database(self):
        """Vacuum database to reclaim space and optimize storage"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # VACUUM cannot be run inside a transaction
            conn.execute("VACUUM")
            
            conn.close()
            
            self.logger.info("Database vacuum completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Error vacuuming database: {str(e)}")
            return False
    
    def get_table_stats(self):
        """Get statistics about database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            stats = {}
            for table in tables:
                table_name = table[0]
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                
                # Get table info
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                stats[table_name] = {
                    'row_count': row_count,
                    'column_count': len(columns),
                    'columns': [col[1] for col in columns]
                }
            
            conn.close()
            
            self.logger.info(f"Retrieved statistics for {len(stats)} tables")
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting table stats: {str(e)}")
            return {}
    
    def optimize_queries(self):
        """Run common query optimizations"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Enable query planner optimizations
            cursor.execute("PRAGMA optimize")
            
            # Set optimal cache size (in KB)
            cursor.execute("PRAGMA cache_size = 10000")  # 10MB cache
            
            # Set journal mode to WAL for better concurrency
            cursor.execute("PRAGMA journal_mode = WAL")
            
            # Set synchronous mode to NORMAL for better performance
            cursor.execute("PRAGMA synchronous = NORMAL")
            
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")
            
            conn.commit()
            conn.close()
            
            self.logger.info("Query optimizations applied")
            return True
            
        except Exception as e:
            self.logger.error(f"Error optimizing queries: {str(e)}")
            return False
    
    def cleanup_old_data(self, days_to_keep=90):
        """Clean up old data to improve performance"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Clean up old cache entries
            cursor.execute("DELETE FROM cache_entries WHERE expires_at < datetime('now')")
            expired_cache_count = cursor.rowcount
            
            # Clean up old stock movements (keep last 90 days)
            cursor.execute("""
                DELETE FROM stock_movements 
                WHERE movement_date < date('now', '-{} days')
            """.format(days_to_keep))
            old_movements_count = cursor.rowcount
            
            # Clean up old loyalty point transactions (keep last 90 days)
            cursor.execute("""
                DELETE FROM loyalty_points 
                WHERE transaction_date < date('now', '-{} days')
                AND transaction_type = 'earned'
            """.format(days_to_keep))
            old_points_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Cleaned up: {expired_cache_count} expired cache entries, "
                           f"{old_movements_count} old stock movements, "
                           f"{old_points_count} old loyalty points")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {str(e)}")
            return False
    
    def run_full_optimization(self):
        """Run complete database optimization"""
        self.logger.info("Starting full database optimization...")
        
        results = {
            'indexes': self.create_indexes(),
            'analyze': self.analyze_database(),
            'queries': self.optimize_queries(),
            'cleanup': self.cleanup_old_data(),
            'vacuum': self.vacuum_database()
        }
        
        success_count = sum(results.values())
        total_count = len(results)
        
        self.logger.info(f"Database optimization completed: {success_count}/{total_count} operations successful")
        
        # Get final stats
        stats = self.get_table_stats()
        self.logger.info(f"Database contains {len(stats)} tables with total rows: {sum(s['row_count'] for s in stats.values())}")
        
        return results

def optimize_database():
    """Main function to optimize database"""
    optimizer = DatabaseOptimizer()
    return optimizer.run_full_optimization()

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run optimization
    results = optimize_database()
    print(f"Optimization results: {results}")

