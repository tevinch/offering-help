# One cache fill per asyncio key

Cachetory 3.5.1's `@cached` reads the cache, calls the wrapped function on a miss, then stores the result. Simultaneous misses can therefore call the source multiple times. `if_not_exists=True` prevents overwriting an existing cached value; it does not coordinate the earlier source calls.

For requests handled by **one asyncio event loop in one process**, this example puts a lock around each key's fill and checks the cache again after acquiring it. Waiting callers then use the newly cached value. Different keys can load concurrently.

## Run

Tested with Python 3.12.4 and Cachetory 3.5.1. From this directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
.venv/bin/python demo.py
.venv/bin/python -m unittest -v
```

On Windows, use `.venv\Scripts\python.exe` for the Python commands. The demo uses an in-memory cache and synthetic strings; it needs no Redis instance or network service after installation.

Expected output:

```text
if_not_exists=True: 8 callers, 8 source calls
generation-1: 8 callers, 1 fill; later hit uses cached value
item expired; next batch must load fresh data
generation-2: 8 callers, 1 fill; later hit uses cached value
unrelated cached value preserved
```

The first batch calls the real `@cached(if_not_exists=True)` decorator. The later batches use the helper, including a real expiration through `cache.expire_in`. The tests check returned values and cache contents, independent-key progress, cached `None`, failed-fill recovery and cancellation of a waiting caller.

## Use in an application

Keep the same `CoalescedCache` instance for all callers sharing a cache. Pass an async function that takes no arguments and returns the value:

```python
from datetime import timedelta
from coalesced_cache import CoalescedCache

fills = CoalescedCache(cache)  # Your existing asynchronous Cachetory cache.

async def get_document(document_id):
    return await fills.get_or_fill(
        f"document:{document_id}",
        lambda: read_document(document_id),  # Your async source reader.
        ttl=timedelta(minutes=1),
    )
```

Use consistent source functions and TTLs for a given key, and use this path for every fill of that key. Include every input that changes the value in the cache key. The lock protects the complete `read → load → store` operation; putting it only inside an already decorated source function omits the second cache check and can still repeat the load.

`None` is a valid cached value. A source or cache error propagates. Failed or cancelled fills do not retain the lock; a waiting caller can attempt a new fill. Cancelling a caller that is only waiting does not cancel the active fill. The helper supplies no retry limit or source timeout; apply the application's own policy to its source reader. It does not serve stale data. If the value expires again before a waiter reads it, that waiter will load it again.

This is local task coordination. Multiple worker processes, machines or event loops do not share these locks, even if they share Redis. It does not coordinate other writers or invalidations that bypass the helper. A loader must not recursively request the same key through this instance. The in-memory/no-operation backend returns stored objects without copying them; the demo uses immutable strings.

## References

- [Cachetory 3.5.1 async decorator](https://github.com/kpn/cachetory/blob/3.5.1/cachetory/decorators/async_.py)
- [Cachetory cache API](https://kpn.github.io/cachetory/caches/)
- [Memory backend caveats](https://kpn.github.io/cachetory/backends/memory/)
- [Python asyncio locks](https://docs.python.org/3/library/asyncio-sync.html#lock)
- [Original question](https://github.com/kpn/cachetory/issues/181)

## Optional coffee

This example is free to use. If it helped, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
