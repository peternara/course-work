import torch.nn.modules.loss as loss
from torch.nn import functional as F
import numpy as np
import torch
from torch.autograd import Variable


# https://arxiv.org/pdf/1706.07567.pdf
# Sampling Matters in Deep Embedding Learning


class margin_loss(loss._Loss):
    """Creates a criterion that measures the mean absolute value of the
    element-wise difference between input `x` and target `y`:

    D_ij = euclidean distance between representations x_i and x_j
    y_ij = 1 if x_i and x_j represent the same object
    y_ij = -1 otherwise

    margin(i, j) := (\alpha + y_ij (D_ij − \betha))+
    {loss}(x, y)  = (1/n) * sum_ij (margin(i, j))
.

    `x` and `y` 2D Tensor of size `(minibatch, n)`

    The sum operation still operates over all the elements, and divides by `n`.

    The division by `n` can be avoided if one sets the constructor argument
    `size_average=False`.

    Args:
        size_average (bool, optional): By default, the losses are averaged
           over observations for each minibatch. However, if the field
           size_average is set to False, the losses are instead summed for
           each minibatch. Default: True

    Shape:
        - Input: :math:`(N, *)` where `*` means, any number of additional
          dimensions
        - Target: :math:`(N, *)`, same shape as the input
    """

    def __init__(self, alpha=1.5, betha=0.3):
        super(margin_loss, self).__init__()
        self.alpha = alpha
        self.bethe = betha

    def forward(self, input, target):
        loss._assert_no_grad(target)

        n = input.data.shape[0]

        distances = Variable(torch.zeros(int((n * (n-1))/2)).cuda())
        labels = target.data.cpu().numpy()
        k = 0
        result = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                distances[k] = torch.dist(input[i], input[j])

                if labels[i] != labels[j]:
                    y = -1.0
                else:
                    y = 1.0

                result = result + torch.clamp(self.alpha + y * (distances[k] - self.bethe), min=0.0)
                k = k + 1

        if self.size_average:
            result = torch.mean(result)
        return result