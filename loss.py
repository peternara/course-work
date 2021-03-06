import numpy as np
import torch
import torch.nn.modules.loss as loss
from torch.autograd import Variable


# https://arxiv.org/pdf/1706.07567.pdf
# Sampling Matters in Deep Embedding Learning


class MarginLoss(loss._Loss):
    """
    D_ij =  euclidean distance between representations x_i and x_j
    y_ij =  1 if x_i and x_j represent the same object
    y_ij = -1 otherwise

    margin(i, j) := (alpha + y_ij (D_ij − bethe))+
    {loss}        = (1/n) * sum_ij (margin(i, j))
.
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

    def __init__(self, alpha=0.3, bethe=1.2):
        super(MarginLoss, self).__init__()
        self.alpha = alpha
        self.bethe = bethe
        print('self.alpha = ',self.alpha)
        print('self.bethe = ', self.bethe)

    @staticmethod
    # returns a vector of pairwise distances between
    # the image number i and all images from
    # i + 1 till n
    def get_distances_i(i, input, n, representation_vector_length):
        pdist = torch.nn.PairwiseDistance(p=2).cuda()
        return pdist(Variable(torch.ones([n - i - 1,
                                          representation_vector_length]).cuda()) *
                     input[i].cuda(),
                     input[i + 1:].cuda())

    @staticmethod
    # returns signs for pairs of image number i and all image from i + 1 till n
    def get_signs_i(i, target, n):
        # we need
        #    y_ij =  1 if x_i and x_j represent the same object
        #    y_ij = -1 otherwise

        # here distance wil be 0 for images with equal targets (labels) and non-zero for non equal
        distances_for_signs = \
            Variable(torch.ones([n - i - 1]).cuda()) * target[i].float().cuda() - \
                                                       target[i + 1:].float().cuda()
        # we should map 0 --> 1 and non-zeero --> -1
        list_of_signs = list(map(lambda d: 1.0 if d == 0.0 else -1.0, distances_for_signs.data))
        return Variable(torch.from_numpy(np.array(list_of_signs)).float().cuda())

    @staticmethod
    # here we add new result value to the given result value and return the sum
    def get_result_i(self, i, distances_i, target, result, n):
        m = distances_i.data.shape[0]

        signs = self.get_signs_i(i, target, n)
        distances_i_bethe = torch.add(distances_i[:, 0],  -self.bethe)

        distances_i_bethe_star_signs = distances_i_bethe * signs

        distances_i_bethe_star_signs_alpha = torch.add(distances_i_bethe_star_signs, self.alpha)

        result = result + torch.sum(torch.clamp(distances_i_bethe_star_signs_alpha, min=0.0).cuda())

        return result

    def forward(self, input, target):
        loss._assert_no_grad(target)

        n = input.data.shape[0]
        representation_vector_length = input[0].data.shape[0]

        # we should sum up distances for all pairs of inputs
        result = 0.0
        for i in range(n - 1):
            distances_i = self.get_distances_i(i, input, n, representation_vector_length)
            result = self.get_result_i(self, i, distances_i, target, result, n)
            #print('result ', result, 'i = ', i)

        if self.size_average:
            #result = torch.mean(result).cuda()
            result = torch.div(result, float(n))

        return result
