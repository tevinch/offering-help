"""Weighted edge aggregation using native PyTorch operations."""
import torch


def weighted_sum(alpha, x, index, num_segments):
    """alpha[E,H,1], x[E,H,C], index[E] -> output[num_segments,H,C].

    Inputs share device and floating dtype; index is int64 and in range.
    The compiled callable lets Inductor fuse the product into the reduction.
    """
    output = x.new_zeros((num_segments, x.shape[1], x.shape[2]))
    return output.index_add(0, index, alpha * x)


compiled_weighted_sum = torch.compile(weighted_sum, fullgraph=True)
