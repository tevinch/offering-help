"""Coordinate cache fills within one asyncio event loop."""

import asyncio
from weakref import WeakValueDictionary


class CoalescedCache:
    """Share one instance per cache and event loop; use consistent keys/loaders."""

    def __init__(self, cache):
        self.cache = cache
        self._locks = WeakValueDictionary()

    async def get_or_fill(self, key, loader, ttl=None):
        """Get a value, or fill it while other callers for this key wait.

        Errors propagate without caching. A later waiting caller may retry.
        This coordinates tasks in one loop, not threads or worker processes.
        """
        missing = object()
        value = await self.cache.get(key, missing)
        if value is not missing:
            return value

        # No await between lookup and insertion: other tasks cannot interleave.
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock

        # Keep a strong reference while waiting/holding the lock. Idle keys drop
        # out of the weak map rather than accumulating for the process lifetime.
        async with lock:
            # The previous holder may have populated the cache while we waited.
            value = await self.cache.get(key, missing)
            if value is missing:
                value = await loader()
                await self.cache.set(key, value, time_to_live=ttl)
            return value
