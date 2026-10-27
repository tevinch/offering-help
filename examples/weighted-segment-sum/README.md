# Weighted segment sums without the full product buffer

For graph attention with `alpha[E,H,1]` and `x[E,H,C]`, computing
`segment_sum_coo(alpha * x, index)` first creates an `E × H × C` product.
Keep the multiplication inside a compiled native PyTorch reduction so Inductor can fuse it.

Use the `alpha` tensor you already obtain from `scatter_softmax` in your existing,
compatible torch-scatter environment:

```python
from weighted_sum import compiled_weighted_sum

result = compiled_weighted_sum(alpha, x, index, num_segments)
loss = loss_function(result)
loss.backward()
optimizer.step()
```

The complete operation is small:

```python
def weighted_sum(alpha, x, index, num_segments):
    output = x.new_zeros((num_segments, x.shape[1], x.shape[2]))
    return output.index_add(0, index, alpha * x)

compiled_weighted_sum = torch.compile(weighted_sum, fullgraph=True)
```

Pass the two factors separately. Passing an already computed `alpha * x` into the
compiled function retains the large temporary. This uses public PyTorch operations;
it does not add an API to torch-scatter.

## Run the checks

With a supported C++ compiler available for CPU Inductor:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install torch==2.14.1
python -m unittest -v
python memory_check.py
```

The tests check weighted values against a hand-calculated fixture, float32/float64,
multiple heads, missing/trailing empty segments, noncontiguous features, empty edges,
first-order gradients, and completed SGD updates against an independent per-group reduction.

To check the original `torch_scatter.scatter_softmax` and `segment_sum_coo` workflow,
run `python compare_scatter.py` in an environment with a matching torch-scatter binary.
The reference check was run on PyTorch 2.12.0 and torch-scatter 2.1.2 using the
[official CPU wheel index](https://data.pyg.org/whl/torch-2.12.0+cpu.html).
It checks normalization, output, loss, gradients of logits/features, and the updated parameters.
The native recipe and its tests also ran on current stable PyTorch 2.14.1.
The 2.14 CPU extension index does not currently list a torch-scatter wheel;
do not install a wheel built for another PyTorch version.

## Observed memory

`memory_check.py` profiles warmed eager and compiled operations in separate processes.
On macOS arm64, CPU, PyTorch 2.14.1, float32, `E=4096`, `H=4`, `C=32`, and 128 segments:

| Profiled operation | Eager peak new tensor bytes | Compiled peak new tensor bytes |
| --- | ---: | ---: |
| Forward | 2,228,224 | 65,536 |
| Forward + backward | 6,422,536 | 2,293,768 |

The product alone would occupy 2,097,152 bytes. Compiled forward recorded one allocation,
exactly the 65,536-byte output. Backward still needs the feature gradient of size `[E,H,C]`
and the weight gradient of size `[E,H,1]`; these are included in the training measurement.
These are PyTorch CPU tensor allocations during the operation, excluding existing inputs,
compiler work and total process memory. They do not establish CUDA memory savings or speed.
Run the check with your actual sizes, PyTorch version and device before relying on it.

## Input and compiler constraints

- `alpha` has shape `[E,H,1]`; `x` has shape `[E,H,C]`, on the same device and floating dtype.
- `index` is a one-dimensional int64 tensor with `E` valid segment indices.
  `num_segments` includes missing and trailing groups. Existing sorted COO indices work.
- Only CPU float32/float64 and ordinary first-order backward were checked here.
  CUDA, MPS, mixed precision, higher-order gradients and compiler integration with a larger
  model have not been checked. A smaller local example cannot guarantee that a full model fits.
- The first call compiles. New shapes or strides can trigger recompilation.
  `fullgraph=True` reports unsupported graph capture instead of accepting graph breaks.
  Keep compilation enabled and inspect your own profiler; an eager fallback retains the product.
- Floating-point summation order can differ from `segment_sum_coo`; use suitable tolerances.
  No bitwise or cross-device determinism is promised.

[PyTorch compilation guidance](https://docs.pytorch.org/docs/stable/torch.compiler.html),
[`index_add` API](https://docs.pytorch.org/docs/stable/generated/torch.Tensor.index_add.html),
and [torch-scatter COO semantics](https://pytorch-scatter.readthedocs.io/en/latest/functions/segment_coo.html).
The related [weighted-add discussion](https://github.com/rusty1s/pytorch_scatter/issues/314)
also points to `torch.compile`.

## Optional coffee

The example is free. If it saves you time, a coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
