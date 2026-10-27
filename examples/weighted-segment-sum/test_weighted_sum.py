"""Run with python -m unittest -v; no extension is required."""
import unittest

import torch

from weighted_sum import compiled_weighted_sum


def grouped_softmax(scores, index, segments):
    """Independent per-group softmax for the small training fixture."""
    parts = [torch.softmax(scores[index == i], dim=0) for i in range(segments)]
    return torch.cat(parts) if scores.shape[0] else scores


def reference(alpha, x, index, segments):
    return torch.stack([(alpha[index == i] * x[index == i]).sum(0)
                        for i in range(segments)])


class WeightedSumTests(unittest.TestCase):
    def test_weighted_values_and_empty_segments(self):
        # Dropping weights, changing the reduction axis or omitting empty groups fails.
        index = torch.tensor([0, 0, 2])
        alpha = torch.tensor([[[0.25]], [[0.75]], [[1.0]]])
        x = torch.tensor([[[2.0, 4.0]], [[6.0, 8.0]], [[10.0, 12.0]]])
        expected = torch.tensor([[[5.0, 7.0]], [[0.0, 0.0]],
                                 [[10.0, 12.0]], [[0.0, 0.0]]])
        torch.testing.assert_close(compiled_weighted_sum(alpha, x, index, 4), expected)

    def test_completed_training_step_matches_independent_group_reduction(self):
        # Detaching either input, losing a group or incorrect backward changes updates.
        for dtype in (torch.float32, torch.float64):
            for noncontiguous in (False, True):
                with self.subTest(dtype=dtype, noncontiguous=noncontiguous):
                    torch.manual_seed(5)
                    index = torch.tensor([0, 0, 2, 2, 2, 4, 4])
                    scores = torch.randn(7, 2, 1, dtype=dtype, requires_grad=True)
                    data = torch.randn(7, 3, 2, dtype=dtype).transpose(1, 2)
                    x = (data if noncontiguous else data.contiguous()).detach().requires_grad_()
                    expected_scores = scores.detach().clone().requires_grad_()
                    expected_x = x.detach().clone().requires_grad_()
                    old_scores, old_x = scores.detach().clone(), x.detach().clone()
                    target = torch.linspace(-1, 1, 36, dtype=dtype).reshape(6, 2, 3)
                    actual_optimizer = torch.optim.SGD([scores, x], lr=0.05)
                    expected_optimizer = torch.optim.SGD([expected_scores, expected_x], lr=0.05)
                    output = compiled_weighted_sum(grouped_softmax(scores, index, 6), x, index, 6)
                    expected = reference(grouped_softmax(expected_scores, index, 6),
                                         expected_x, index, 6)
                    torch.testing.assert_close(output, expected)
                    loss = (output - target).square().mean()
                    expected_loss = (expected - target).square().mean()
                    loss.backward()
                    expected_loss.backward()
                    for actual, want in ((scores.grad, expected_scores.grad), (x.grad, expected_x.grad)):
                        self.assertIsNotNone(actual)
                        self.assertTrue(torch.isfinite(actual).all())
                        torch.testing.assert_close(actual, want)
                    actual_optimizer.step()
                    expected_optimizer.step()
                    torch.testing.assert_close(scores, expected_scores)
                    torch.testing.assert_close(x, expected_x)
                    self.assertFalse(torch.equal(scores.detach(), old_scores))
                    self.assertFalse(torch.equal(x.detach(), old_x))

    def test_empty_edges_complete_backward(self):
        # Returning unrelated zeros would lose these defined empty gradients.
        alpha = torch.empty(0, 2, 1, requires_grad=True)
        x = torch.empty(0, 2, 3, requires_grad=True)
        output = compiled_weighted_sum(alpha, x, torch.empty(0, dtype=torch.long), 4)
        torch.testing.assert_close(output, torch.zeros(4, 2, 3))
        output.sum().backward()
        self.assertEqual(alpha.grad.shape, alpha.shape)
        self.assertEqual(x.grad.shape, x.shape)


if __name__ == '__main__':
    torch.set_num_threads(1)
    unittest.main()
