"""Verify the original torch-scatter softmax -> weighted reduction -> SGD workflow.

Requires an installed torch-scatter binary matching this PyTorch environment.
"""
import importlib.metadata
import json

import torch
from torch_scatter import scatter_softmax, scatter_sum, segment_sum_coo

from weighted_sum import compiled_weighted_sum


def train(reduce, initial_scores, initial_x, index, segments):
    scores = initial_scores.clone().requires_grad_()
    x = initial_x.clone().requires_grad_()
    optimizer = torch.optim.SGD([scores, x], lr=0.01)
    alpha = scatter_softmax(scores, index, dim=0, dim_size=segments)
    normalization = scatter_sum(alpha, index, dim=0, dim_size=segments)
    present = torch.zeros(segments, dtype=torch.bool)
    present[index] = True
    torch.testing.assert_close(normalization[present], torch.ones_like(normalization[present]))
    output = reduce(alpha, x, index, segments)
    target = torch.linspace(-0.5, 0.5, output.numel()).reshape_as(output)
    loss = (output - target).square().mean()
    loss.backward()
    assert scores.grad is not None and x.grad is not None
    assert torch.isfinite(scores.grad).all() and torch.isfinite(x.grad).all()
    gradients = (scores.grad.clone(), x.grad.clone())
    optimizer.step()
    assert not torch.equal(scores, initial_scores)
    assert not torch.equal(x, initial_x)
    return output.detach(), loss.detach(), gradients, (scores.detach(), x.detach())


if __name__ == '__main__':
    torch.set_num_threads(1)
    torch.manual_seed(23)
    index = torch.tensor([0, 0, 2, 2, 2, 4, 4])
    scores = torch.randn(7, 3, 1)
    x = torch.randn(7, 3, 8)
    expected = train(lambda a, v, i, n: segment_sum_coo(a * v, i, dim_size=n),
                     scores, x, index, 6)
    actual = train(compiled_weighted_sum, scores, x, index, 6)
    errors = {}
    for name, got, want in [('output', actual[0], expected[0]),
                            ('loss', actual[1], expected[1]),
                            ('logits_gradient', actual[2][0], expected[2][0]),
                            ('features_gradient', actual[2][1], expected[2][1]),
                            ('logits_after_sgd', actual[3][0], expected[3][0]),
                            ('features_after_sgd', actual[3][1], expected[3][1])]:
        torch.testing.assert_close(got, want)
        errors[name] = (got - want).abs().max().item()
    print(json.dumps({'torch': torch.__version__,
                      'torch_scatter': importlib.metadata.version('torch-scatter'),
                      'device': 'cpu', 'scatter_softmax_normalized': True,
                      'optimizer_step_completed': True, 'max_absolute_errors': errors}, indent=2))
