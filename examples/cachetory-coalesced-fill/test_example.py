import asyncio
import unittest
from datetime import timedelta

from cachetory.backends.async_ import MemoryBackend
from cachetory.caches.async_ import Cache
from cachetory.serializers import NoopSerializer

from coalesced_cache import CoalescedCache


class FillTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.cache = Cache(backend=MemoryBackend(), serializer=NoopSerializer())
        self.fills = CoalescedCache(self.cache)

    async def asyncTearDown(self):
        await self.cache.__aexit__(None, None, None)

    async def test_concurrent_misses_hits_and_real_expiry(self):
        # Missing the lock or its second read causes duplicate source calls.
        await self.cache.set('existing', 'keep me')
        calls = 0

        async def load():
            nonlocal calls
            calls += 1
            value = f'generation-{calls}'
            await asyncio.sleep(0)
            return value

        for expected, count in [('generation-1', 1), ('generation-2', 2)]:
            values = await asyncio.wait_for(asyncio.gather(*[
                self.fills.get_or_fill('item', load, timedelta(minutes=1))
                for _ in range(8)
            ]), 5)
            self.assertEqual(values, [expected] * 8)
            self.assertEqual(calls, count)
            self.assertEqual(await self.cache.get('item'), expected)
            self.assertEqual(await self.fills.get_or_fill('item', load), expected)
            self.assertEqual(calls, count)
            self.assertEqual(await self.cache.get('existing'), 'keep me')
            await self.cache.expire_in('item', timedelta(0))
            missing = object()
            self.assertIs(await self.cache.get('item', missing), missing)

    async def test_different_keys_make_progress_together(self):
        # A global lock would prevent the second loader from starting.
        entered = {key: asyncio.Event() for key in ['a', 'b']}
        release = asyncio.Event()

        async def load(key):
            entered[key].set()
            await release.wait()
            return f'value-{key}'

        tasks = [asyncio.create_task(self.fills.get_or_fill(
            key, lambda key=key: load(key))) for key in ['a', 'b']]
        try:
            await asyncio.wait_for(asyncio.gather(
                entered['a'].wait(), entered['b'].wait()), 5)
        finally:
            release.set()
            values = await asyncio.gather(*tasks)
        self.assertEqual(values, ['value-a', 'value-b'])
        self.assertEqual(await self.cache.get_many('a', 'b'),
                         {'a': 'value-a', 'b': 'value-b'})

    async def test_none_is_cached(self):
        # Treating None as a miss would call the source again.
        calls = 0

        async def load():
            nonlocal calls
            calls += 1
            return None

        self.assertIsNone(await self.fills.get_or_fill('empty', load))
        self.assertIsNone(await self.fills.get_or_fill('empty', load))
        self.assertEqual(calls, 1)
        self.assertEqual(await self.cache.get_many('empty'), {'empty': None})

    async def test_failed_fill_can_be_retried(self):
        # Caching an exception or retaining a locked key blocks recovery.
        async def fail():
            raise ValueError('source unavailable')

        with self.assertRaisesRegex(ValueError, 'source unavailable'):
            await self.fills.get_or_fill('item', fail)
        self.assertEqual(await self.cache.get_many('item'), {})

        async def succeed():
            return 'recovered'

        value = await asyncio.wait_for(self.fills.get_or_fill('item', succeed), 5)
        self.assertEqual(value, 'recovered')
        self.assertEqual(await self.cache.get('item'), 'recovered')

    async def test_cancelling_waiter_keeps_running_fill(self):
        # Sharing cancellation with the active loader would lose its result.
        started, release = asyncio.Event(), asyncio.Event()
        calls = 0

        async def load():
            nonlocal calls
            calls += 1
            started.set()
            await release.wait()
            return 'ready'

        first = asyncio.create_task(self.fills.get_or_fill('item', load))
        await asyncio.wait_for(started.wait(), 5)
        waiter = asyncio.create_task(self.fills.get_or_fill('item', load))
        await asyncio.sleep(0)
        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await waiter
        release.set()
        self.assertEqual(await asyncio.wait_for(first, 5), 'ready')
        self.assertEqual(await self.cache.get('item'), 'ready')
        self.assertEqual(calls, 1)


if __name__ == '__main__':
    unittest.main()
