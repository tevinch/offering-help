"""Compare warmed CPU tensor allocations in separate eager/compiled processes."""
import argparse
import gc
import json
import subprocess
import sys
import tempfile

import torch
from torch.profiler import ProfilerActivity, profile

from weighted_sum import compiled_weighted_sum, weighted_sum

E, H, C, N = 4096, 4, 32, 128


def inputs():
    index = torch.arange(E, dtype=torch.long) // (E // N)
    alpha = torch.randn(E, H, 1, requires_grad=True)
    x = torch.randn(E, H, C, requires_grad=True)
    return alpha, x, index


def measure(fn, backward):
    alpha, x, index = inputs()
    with profile(activities=[ProfilerActivity.CPU], profile_memory=True,
                 record_shapes=True, acc_events=True) as observation:
        result = fn(alpha, x, index, N)
        if backward:
            result.sum().backward()
    with tempfile.NamedTemporaryFile(suffix='.json') as trace:
        observation.export_chrome_trace(trace.name)
        # The exporter may replace the path, so reopen its completed output.
        with open(trace.name) as recorded_trace:
            events = json.load(recorded_trace)['traceEvents']
    allocations = [event for event in events if event.get('name') == '[memory]'
                   and event['args'].get('Device Type') == 0]
    if not allocations:
        raise RuntimeError('The profiler did not record CPU allocation events.')
    baseline = allocations[0]['args']['Total Allocated'] - allocations[0]['args']['Bytes']
    peak = max(event['args']['Total Allocated'] for event in allocations) - baseline
    return {'peak_new_tensor_bytes': peak,
            'largest_allocation_bytes': max(event['args']['Bytes'] for event in allocations),
            'allocation_event_count': len(allocations)}


def worker(mode):
    torch.set_num_threads(1)
    fn = compiled_weighted_sum if mode == 'compiled' else weighted_sum
    # Compile both passes before measuring; discard all warmup tensors.
    alpha, x, index = inputs()
    fn(alpha, x, index, N).sum().backward()
    del alpha, x, index
    gc.collect()
    forward = measure(fn, False)
    gc.collect()
    training = measure(fn, True)
    return {'mode': mode, 'torch': torch.__version__, 'device': 'cpu',
            'shape': [E, H, C], 'segments': N,
            'full_product_bytes': E * H * C * 4,
            'output_bytes': N * H * C * 4,
            'required_input_gradient_bytes': (E * H * C + E * H) * 4,
            'forward': forward, 'forward_and_backward': training}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', choices=['eager', 'compiled'])
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker)))
    else:
        reports = {}
        for mode in ('eager', 'compiled'):
            completed = subprocess.run([sys.executable, __file__, '--worker', mode],
                                       text=True, capture_output=True, check=True)
            reports[mode] = json.loads(completed.stdout)
        eager, compiled = reports['eager'], reports['compiled']
        assert compiled['forward']['peak_new_tensor_bytes'] < compiled['full_product_bytes']
        assert (compiled['forward_and_backward']['peak_new_tensor_bytes'] <
                eager['forward_and_backward']['peak_new_tensor_bytes'])
        print(json.dumps(reports, indent=2))
