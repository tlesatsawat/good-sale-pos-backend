import time
import json
import hashlib
import logging
from datetime import datetime, timedelta
from functools import wraps
from collections import OrderedDict
import threading

class MemoryCache:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self, max_size=1000, default_ttl=300):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
    
    def _is_expired(self, entry):
        """Check if cache entry is expired"""
        return datetime.now() > entry['expires_at']
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        with self.lock:
            expired_keys = [
                key for key, entry in self.cache.items()
                if self._is_expired(entry)
            ]
            for key in expired_keys:
                del self.cache[key]
    
    def _evict_lru(self):
        """Evict least recently used entries if cache is full"""
        with self.lock:
            while len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
    
    def get(self, key):
        """Get value from cache"""
        with self.lock:
            if key not in self.cache:
                return None
            
            entry = self.cache[key]
            
            if self._is_expired(entry):
                del self.cache[key]
                return None
            
            # Move to end (mark as recently used)
            self.cache.move_to_end(key)
            return entry['value']
    
    def set(self, key, value, ttl=None):
        """Set value in cache"""
        if ttl is None:
            ttl = self.default_ttl
        
        with self.lock:
            expires_at = datetime.now() + timedelta(seconds=ttl)
            
            self.cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': datetime.now()
            }
            
            # Move to end (mark as recently used)
            self.cache.move_to_end(key)
            
            # Cleanup and evict if necessary
            self._cleanup_expired()
            self._evict_lru()
    
    def delete(self, key):
        """Delete key from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
    
    def get_stats(self):
        """Get cache statistics"""
        with self.lock:
            self._cleanup_expired()
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hit_ratio': getattr(self, '_hit_count', 0) / max(getattr(self, '_total_requests', 1), 1),
                'entries': list(self.cache.keys())
            }

class CacheManager:
    """Centralized cache management"""
    
    def __init__(self):
        self.caches = {
            'menu': MemoryCache(max_size=500, default_ttl=600),  # 10 minutes
            'reports': MemoryCache(max_size=100, default_ttl=300),  # 5 minutes
            'packages': MemoryCache(max_size=50, default_ttl=3600),  # 1 hour
            'stores': MemoryCache(max_size=200, default_ttl=300),  # 5 minutes
            'orders': MemoryCache(max_size=1000, default_ttl=60),  # 1 minute
        }
        self.logger = logging.getLogger(__name__)
    
    def get_cache(self, cache_name):
        """Get specific cache instance"""
        return self.caches.get(cache_name)
    
    def clear_all(self):
        """Clear all caches"""
        for cache in self.caches.values():
            cache.clear()
        self.logger.info("All caches cleared")
    
    def get_all_stats(self):
        """Get statistics for all caches"""
        stats = {}
        for name, cache in self.caches.items():
            stats[name] = cache.get_stats()
        return stats

# Global cache manager instance
cache_manager = CacheManager()

def cache_key(*args, **kwargs):
    """Generate cache key from arguments"""
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items())
    }
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_string.encode()).hexdigest()

def cached(cache_name='default', ttl=300, key_func=None):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get cache instance
            cache = cache_manager.get_cache(cache_name)
            if not cache:
                # If cache doesn't exist, just execute function
                return func(*args, **kwargs)
            
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = f"{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = cache.get(key)
            if cached_result is not None:
                cache_manager.logger.debug(f"Cache hit for {key}")
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            cache_manager.logger.debug(f"Cache miss for {key}, result cached")
            
            return result
        return wrapper
    return decorator

def invalidate_cache(cache_name, pattern=None):
    """Invalidate cache entries"""
    cache = cache_manager.get_cache(cache_name)
    if cache:
        if pattern:
            # Invalidate entries matching pattern
            with cache.lock:
                keys_to_delete = [
                    key for key in cache.cache.keys()
                    if pattern in key
                ]
                for key in keys_to_delete:
                    cache.delete(key)
        else:
            # Clear entire cache
            cache.clear()

# Database query optimization
class QueryOptimizer:
    """Database query optimization utilities"""
    
    def __init__(self):
        self.query_stats = {}
        self.slow_queries = []
        self.logger = logging.getLogger(__name__)
    
    def log_query(self, query, execution_time, params=None):
        """Log query execution for analysis"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        
        if query_hash not in self.query_stats:
            self.query_stats[query_hash] = {
                'query': query,
                'count': 0,
                'total_time': 0,
                'avg_time': 0,
                'max_time': 0
            }
        
        stats = self.query_stats[query_hash]
        stats['count'] += 1
        stats['total_time'] += execution_time
        stats['avg_time'] = stats['total_time'] / stats['count']
        stats['max_time'] = max(stats['max_time'], execution_time)
        
        # Log slow queries
        if execution_time > 1.0:  # Queries taking more than 1 second
            slow_query = {
                'query': query,
                'execution_time': execution_time,
                'params': params,
                'timestamp': datetime.now()
            }
            self.slow_queries.append(slow_query)
            
            # Keep only recent slow queries
            if len(self.slow_queries) > 100:
                self.slow_queries.pop(0)
            
            self.logger.warning(f"Slow query detected: {execution_time:.2f}s - {query[:100]}...")
    
    def get_query_stats(self):
        """Get query performance statistics"""
        return {
            'total_queries': len(self.query_stats),
            'slow_queries_count': len(self.slow_queries),
            'top_slow_queries': sorted(
                self.query_stats.values(),
                key=lambda x: x['avg_time'],
                reverse=True
            )[:10]
        }
    
    def get_slow_queries(self, limit=10):
        """Get recent slow queries"""
        return self.slow_queries[-limit:] if self.slow_queries else []

# Global query optimizer instance
query_optimizer = QueryOptimizer()

def monitor_query(func):
    """Decorator to monitor database query performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Extract query from function name or arguments
            query = getattr(func, '__name__', 'unknown_query')
            query_optimizer.log_query(query, execution_time)
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            query_optimizer.log_query(f"FAILED_{func.__name__}", execution_time)
            raise
    return wrapper

# Cache warming utilities
def warm_cache():
    """Pre-populate cache with frequently accessed data"""
    try:
        # This would be called during application startup
        # to pre-load commonly accessed data
        
        # Example: Pre-load packages
        packages_cache = cache_manager.get_cache('packages')
        if packages_cache:
            # Simulate loading packages data
            packages_data = [
                {'id': 1, 'name': 'Basic', 'price': 299},
                {'id': 2, 'name': 'Pro', 'price': 599},
                {'id': 3, 'name': 'Enterprise', 'price': 999}
            ]
            packages_cache.set('all_packages', packages_data, ttl=3600)
        
        logging.getLogger(__name__).info("Cache warming completed")
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Cache warming failed: {str(e)}")

def init_performance_optimization():
    """Initialize performance optimization systems"""
    # Warm up caches
    warm_cache()
    
    logging.getLogger(__name__).info("Performance optimization initialized")
    
    return cache_manager, query_optimizer

if __name__ == "__main__":
    # Test caching system
    logging.basicConfig(level=logging.INFO)
    
    cache_manager, query_optimizer = init_performance_optimization()
    
    # Test cache operations
    menu_cache = cache_manager.get_cache('menu')
    menu_cache.set('test_menu', {'name': 'Coffee', 'price': 50}, ttl=60)
    
    result = menu_cache.get('test_menu')
    print(f"Cached menu: {result}")
    
    # Test cache decorator
    @cached(cache_name='menu', ttl=300)
    def get_menu_items():
        # Simulate database query
        time.sleep(0.1)
        return [{'name': 'Coffee', 'price': 50}, {'name': 'Tea', 'price': 30}]
    
    # First call - cache miss
    start = time.time()
    items1 = get_menu_items()
    time1 = time.time() - start
    
    # Second call - cache hit
    start = time.time()
    items2 = get_menu_items()
    time2 = time.time() - start
    
    print(f"First call: {time1:.3f}s, Second call: {time2:.3f}s")
    print(f"Cache stats: {cache_manager.get_all_stats()}")

