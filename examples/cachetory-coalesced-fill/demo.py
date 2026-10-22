"""Run the concurrent-fill comparison locally; no external service is used."""

import asyncio
from datetime import timedelta

from cachetory.backends.async_ import MemoryBackend
from cachetory.caches.async_ import Cache
from cachetory.decorators.async_ import cached
from cachetory.serializers import NoopSerializer

from coalesced_cache import CoalescedCache


async def main():
    async with Cache(backend=MemoryBackend(), serializer=NoopSerializer()) as cache:
        baseline_calls = 0
        all_started = asyncio.Event()

        @cached(cache, make_key=lambda *_: 'baseline', if_not_exists=True)
        async def uncoordinated():
            nonlocal baseline_calls
            baseline_calls += 1
            if baseline_calls == 8:
                all_started.set()
            await all_started.wait()
            return 'source value'

        values = await asyncio.wait_for(asyncio.gather(*[
            uncoordinated() for _ in range(8)
        ]), 5)
        assert values == ['source value'] * 8
        assert baseline_calls == 8
        assert await cache.get('baseline') == 'source value'
        print(f'if_not_exists=True: 8 callers, {baseline_calls} source calls')

        fills = CoalescedCache(cache)
        calls = 0

        async def load():
            nonlocal calls
            calls += 1
            value = f'generation-{calls}'
            await asyncio.sleep(0)  # Let the other callers encounter the miss.
            return value

        for expected, expected_calls in [('generation-1', 1), ('generation-2', 2)]:
            values = await asyncio.wait_for(asyncio.gather(*[
                fills.get_or_fill('item', load, timedelta(minutes=1))
                for _ in range(8)
            ]), 5)
            assert values == [expected] * 8
            assert calls == expected_calls
            assert await cache.get('item') == expected
            assert await fills.get_or_fill('item', load) == expected
            assert calls == expected_calls
            assert await cache.get('baseline') == 'source value'
            print(f'{expected}: 8 callers, 1 fill; later hit uses cached value')
            if expected_calls == 1:
                # Public API sets a real expiration; no wall-clock sleep needed.
                await cache.expire_in('item', timedelta(0))
                missing = object()
                assert await cache.get('item', missing) is missing
                print('item expired; next batch must load fresh data')
        print('unrelated cached value preserved')


if __name__ == '__main__':
    asyncio.run(main())
