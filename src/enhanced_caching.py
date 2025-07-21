import time
import json
import hashlib
import sqlite3
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Optional, Dict, List

class EnhancedCache:
    def __init__(self, db_path='pos_database.db', default_ttl=300):
        self.db_path = db_path
        self.default_ttl = default_ttl  # 5 minutes default
        self.logger = logging.getLogger(__name__)
        self.memory_cache = {}  # In-memory cache for frequently accessed data
        self.max_memory_items = 1000
        
    def _get_cache_key(self, key: str, params: Dict = None) -> str:
        """Generate a unique cache key"""
        if params:
            # Sort params for consistent key generation
            sorted_params = json.dumps(params, sort_keys=True)
            key_string = f"{key}:{sorted_params}"
        else:
            key_string = key
        
        # Use hash for long keys
        if len(key_string) > 100:
            return hashlib.md5(key_string.encode()).hexdigest()
        return key_string
    
    def get(self, key: str, params: Dict = None) -> Optional[Any]:
        """Get value from cache"""
        cache_key = self._get_cache_key(key, params)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            item = self.memory_cache[cache_key]
            if item['expires_at'] > time.time():
                self.logger.debug(f"Cache hit (memory): {cache_key}")
                return item['value']
            else:
                # Remove expired item
                del self.memory_cache[cache_key]
        
        # Check database cache
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT cache_value, expires_at FROM cache_entries 
                WHERE cache_key = ? AND expires_at > datetime('now')
            """, (cache_key,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                value = json.loads(result[0])
                expires_at = datetime.fromisoformat(result[1]).timestamp()
                
                # Store in memory cache for faster access
                if len(self.memory_cache) < self.max_memory_items:
                    self.memory_cache[cache_key] = {
                        'value': value,
                        'expires_at': expires_at
                    }
                
                self.logger.debug(f"Cache hit (database): {cache_key}")
                return value
            
        except Exception as e:
            self.logger.error(f"Error getting cache value: {str(e)}")
        
        self.logger.debug(f"Cache miss: {cache_key}")
        return None
    
    def set(self, key: str, value: Any, ttl: int = None, params: Dict = None) -> bool:
        """Set value in cache"""
        cache_key = self._get_cache_key(key, params)
        ttl = ttl or self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)
        expires_timestamp = expires_at.timestamp()
        
        try:
            # Store in memory cache
            if len(self.memory_cache) < self.max_memory_items:
                self.memory_cache[cache_key] = {
                    'value': value,
                    'expires_at': expires_timestamp
                }
            elif cache_key in self.memory_cache:
                # Update existing item
                self.memory_cache[cache_key] = {
                    'value': value,
                    'expires_at': expires_timestamp
                }
            
            # Store in database cache
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO cache_entries (cache_key, cache_value, expires_at, created_at)
                VALUES (?, ?, ?, ?)
            """, (cache_key, json.dumps(value), expires_at.isoformat(), datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            self.logger.debug(f"Cache set: {cache_key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting cache value: {str(e)}")
            return False
    
    def delete(self, key: str, params: Dict = None) -> bool:
        """Delete value from cache"""
        cache_key = self._get_cache_key(key, params)
        
        try:
            # Remove from memory cache
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]
            
            # Remove from database cache
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM cache_entries WHERE cache_key = ?", (cache_key,))
            
            conn.commit()
            conn.close()
            
            self.logger.debug(f"Cache deleted: {cache_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting cache value: {str(e)}")
            return False
    
    def clear_expired(self) -> int:
        """Clear expired cache entries"""
        try:
            # Clear expired memory cache
            current_time = time.time()
            expired_keys = [
                key for key, item in self.memory_cache.items()
                if item['expires_at'] <= current_time
            ]
            
            for key in expired_keys:
                del self.memory_cache[key]
            
            # Clear expired database cache
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM cache_entries WHERE expires_at <= datetime('now')")
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            total_deleted = len(expired_keys) + deleted_count
            self.logger.info(f"Cleared {total_deleted} expired cache entries")
            return total_deleted
            
        except Exception as e:
            self.logger.error(f"Error clearing expired cache: {str(e)}")
            return 0
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear cache entries matching a pattern"""
        try:
            # Clear from memory cache
            matching_keys = [
                key for key in self.memory_cache.keys()
                if pattern in key
            ]
            
            for key in matching_keys:
                del self.memory_cache[key]
            
            # Clear from database cache
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM cache_entries WHERE cache_key LIKE ?", (f"%{pattern}%",))
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            total_deleted = len(matching_keys) + deleted_count
            self.logger.info(f"Cleared {total_deleted} cache entries matching pattern: {pattern}")
            return total_deleted
            
        except Exception as e:
            self.logger.error(f"Error clearing cache pattern: {str(e)}")
            return 0
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Database cache stats
            cursor.execute("SELECT COUNT(*) FROM cache_entries")
            db_total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM cache_entries WHERE expires_at > datetime('now')")
            db_active = cursor.fetchone()[0]
            
            conn.close()
            
            # Memory cache stats
            current_time = time.time()
            memory_active = sum(
                1 for item in self.memory_cache.values()
                if item['expires_at'] > current_time
            )
            
            return {
                'memory_cache': {
                    'total_items': len(self.memory_cache),
                    'active_items': memory_active,
                    'max_items': self.max_memory_items
                },
                'database_cache': {
                    'total_items': db_total,
                    'active_items': db_active
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {str(e)}")
            return {}

# Global cache instance
cache = EnhancedCache()

def cached(ttl: int = 300, key_prefix: str = "", invalidate_patterns: List[str] = None):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            func_name = f"{key_prefix}{func.__name__}" if key_prefix else func.__name__
            
            # Create params dict from args and kwargs
            params = {
                'args': args,
                'kwargs': kwargs
            }
            
            # Try to get from cache
            cached_result = cache.get(func_name, params)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(func_name, result, ttl, params)
            
            return result
        
        # Add cache invalidation method
        def invalidate(*args, **kwargs):
            func_name = f"{key_prefix}{func.__name__}" if key_prefix else func.__name__
            params = {
                'args': args,
                'kwargs': kwargs
            }
            cache.delete(func_name, params)
            
            # Invalidate patterns if specified
            if invalidate_patterns:
                for pattern in invalidate_patterns:
                    cache.clear_pattern(pattern)
        
        wrapper.invalidate = invalidate
        return wrapper
    
    return decorator

def cache_invalidate_on_change(patterns: List[str]):
    """Decorator to invalidate cache patterns when function is called"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Invalidate cache patterns
            for pattern in patterns:
                cache.clear_pattern(pattern)
            
            return result
        
        return wrapper
    
    return decorator

# Cache management functions
def get_cache_stats():
    """Get cache statistics"""
    return cache.get_stats()

def clear_expired_cache():
    """Clear expired cache entries"""
    return cache.clear_expired()

def clear_cache_pattern(pattern: str):
    """Clear cache entries matching pattern"""
    return cache.clear_pattern(pattern)

def clear_all_cache():
    """Clear all cache entries"""
    try:
        cache.memory_cache.clear()
        
        conn = sqlite3.connect(cache.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache_entries")
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        cache.logger.info(f"Cleared all cache entries: {deleted_count}")
        return deleted_count
        
    except Exception as e:
        cache.logger.error(f"Error clearing all cache: {str(e)}")
        return 0

# Example usage functions with caching
@cached(ttl=600, key_prefix="menu_")  # Cache for 10 minutes
def get_menu_items(store_id: int):
    """Get menu items for a store (cached)"""
    try:
        conn = sqlite3.connect(cache.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, description, price, category, is_available
            FROM menu_items 
            WHERE store_id = ? AND is_available = 1
            ORDER BY category, name
        """, (store_id,))
        
        items = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': item[0],
                'name': item[1],
                'description': item[2],
                'price': float(item[3]),
                'category': item[4],
                'is_available': bool(item[5])
            }
            for item in items
        ]
        
    except Exception as e:
        cache.logger.error(f"Error getting menu items: {str(e)}")
        return []

@cached(ttl=300, key_prefix="packages_")  # Cache for 5 minutes
def get_subscription_packages(pos_type: str = None):
    """Get subscription packages (cached)"""
    packages = [
        {
            'id': 1,
            'name': 'Basic',
            'price': 299,
            'features': ['POS พื้นฐาน', 'รายงานยอดขาย', 'จัดการเมนู'],
            'pos_types': ['restaurant', 'coffee', 'grocery']
        },
        {
            'id': 2,
            'name': 'Professional',
            'price': 599,
            'features': ['POS ครบครัน', 'รายงานขั้นสูง', 'จัดการสต็อก', 'ระบบสมาชิก'],
            'pos_types': ['restaurant', 'coffee', 'grocery']
        },
        {
            'id': 3,
            'name': 'Enterprise',
            'price': 999,
            'features': ['POS แบบองค์กร', 'รายงานแบบ Real-time', 'หลายสาขา', 'API Integration'],
            'pos_types': ['restaurant', 'coffee', 'grocery']
        }
    ]
    
    if pos_type:
        packages = [pkg for pkg in packages if pos_type in pkg['pos_types']]
    
    return packages

@cache_invalidate_on_change(patterns=["menu_", "stock_"])
def update_menu_item(store_id: int, item_id: int, data: Dict):
    """Update menu item and invalidate related cache"""
    # This would update the menu item in database
    # Cache invalidation happens automatically via decorator
    pass

if __name__ == "__main__":
    # Test caching system
    logging.basicConfig(level=logging.INFO)
    
    # Test basic caching
    print("Testing enhanced caching system...")
    
    # Test function caching
    packages = get_subscription_packages()
    print(f"Packages: {len(packages)}")
    
    # Test cache stats
    stats = get_cache_stats()
    print(f"Cache stats: {stats}")
    
    # Test cache clearing
    cleared = clear_expired_cache()
    print(f"Cleared expired entries: {cleared}")

