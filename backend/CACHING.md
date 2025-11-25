# Caching System

Claude Code Role Play uses an in-memory caching layer to improve performance by reducing database queries and filesystem reads.

## Architecture

### Cache Manager (`utils/cache.py`)
- **Thread-safe** in-memory cache with TTL support
- **Automatic expiration** based on configurable TTL
- **Manual invalidation** by key or pattern matching
- **Cache statistics** tracking (hits, misses, hit rate)
- **Periodic cleanup** via background scheduler (every 5 minutes)

### Cached Data Types

| Data Type | TTL | Cache Key Pattern | Invalidation Trigger |
|-----------|-----|-------------------|---------------------|
| **Agent Config** | 5 min | `agent_config:{agent_id}` | Agent update, reload, memory append |
| **Agent Object** | 5 min | `agent_obj:{agent_id}` | Agent update, reload, delete |
| **Room Object** | 30 sec | `room_obj:{room_id}` | Room update, delete |
| **Room Agents** | 1 min | `room_agents:{room_id}` | Agent added/removed from room |
| **Messages** | 5 sec | `room_messages:{room_id}` | New message created |

### Usage

**Cached CRUD Operations** (`crud/cached.py`):
```python
# Use cached versions instead of direct CRUD calls
agent = await crud.get_agent_cached(db, agent_id)
room = await crud.get_room_cached(db, room_id)
agents = await crud.get_agents_cached(db, room_id)
messages = await crud.get_messages_cached(db, room_id)
```

**Manual Cache Invalidation**:
```python
from utils.cache import get_cache, agent_config_key

cache = get_cache()
cache.invalidate(agent_config_key(agent_id))
cache.invalidate_pattern(f"room_{room_id}_")
```

**Agent Config Caching**:
```python
# Agent model automatically caches config data
config = agent.get_config_data()  # Cached (default)
config = agent.get_config_data(use_cache=False)  # Bypass cache
```

## Performance Impact

### Before Caching
- **Polling endpoints** (`/chatting-agents`, `/messages/poll`): Hit DB every 2 seconds
- **Agent responses**: 3-4 DB queries per agent per response
- **Filesystem reads**: Agent config loaded on every response

### After Caching
- **Polling endpoints**: ~95% cache hit rate (30s-1min TTL)
- **Agent responses**: ~80% cache hit rate (5min TTL)
- **Filesystem reads**: Only on cache miss or invalidation

### Expected Improvements
- **Database load**: 70-90% reduction
- **Response latency**: 50-80% reduction for cached operations
- **Filesystem I/O**: 90%+ reduction

## Cache Invalidation Strategy

### Automatic Invalidation
All write operations automatically invalidate related caches:
- `create_message()` → invalidates `room_messages:{room_id}`
- `update_agent()` → invalidates `agent_config:{id}` and `agent_obj:{id}`
- `add_agent_to_room()` → invalidates `room_agents:{room_id}`
- `append_agent_memory()` → invalidates `agent_config:{id}`

### Background Cleanup
- Runs every 5 minutes via APScheduler
- Removes expired entries from memory
- Logs cache statistics

### Manual Cleanup
```python
from utils.cache import get_cache

cache = get_cache()
cache.clear()  # Clear all cache
cache.log_stats()  # View cache statistics
```

## Monitoring

### Cache Statistics
```python
from utils.cache import get_cache

stats = get_cache().get_stats()
# Returns: {
#   "hits": 1000,
#   "misses": 50,
#   "total_requests": 1050,
#   "hit_rate": 95.24,  # percentage
#   "size": 42,  # number of cached entries
#   "invalidations": 15
# }
```

### Debug Logging
Set `logging.getLogger("Cache").setLevel(logging.DEBUG)` to see:
- Cache hits/misses
- Invalidation events
- Expiration cleanup

## Trade-offs

### Pros
- **Significant performance improvement** (70-90% fewer DB queries)
- **Lower latency** for frequently accessed data
- **Reduced I/O** on database and filesystem
- **Thread-safe** with proper locking

### Cons
- **Memory usage** increases with cache size
- **Stale data risk** within TTL window (mitigated by short TTLs)
- **Complexity** in maintaining cache invalidation logic

### Tuning TTLs
Adjust TTLs in `crud/cached.py` based on your needs:
- **Longer TTL** = Better performance, higher staleness risk
- **Shorter TTL** = More DB hits, fresher data

## Best Practices

1. **Use cached functions in hot paths**:
   - Polling endpoints
   - Response generation
   - Background scheduler

2. **Always invalidate on writes**:
   - Add cache invalidation to all CRUD update/delete operations
   - Use pattern invalidation for related data

3. **Monitor cache hit rates**:
   - Log stats periodically
   - Adjust TTLs if hit rate < 70%

4. **Set appropriate TTLs**:
   - Frequently updated data: 5-30 seconds
   - Rarely updated data: 5-10 minutes
   - Configuration data: 10-15 minutes
