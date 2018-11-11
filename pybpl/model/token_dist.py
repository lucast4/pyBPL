from __future__ import division, print_function
from abc import ABCMeta, abstractmethod
import torch
import torch.distributions as dist

from ..parameters import defaultps
from ..part import PartType, StrokeType, PartToken, StrokeToken
from ..concept import ConceptType, CharacterType, ConceptToken, CharacterToken


class ConceptTokenDist(object):
    """
    Defines the distribution P(Token | Type) for concepts
    """
    __metaclass__ = ABCMeta

    def __init__(self, lib):
        self.lib = lib
        self.pdist = PartTokenDist(lib)
        self.rdist = RelationTokenDist(lib)

    @abstractmethod
    def sample_location(self, rtoken, prev_parts):
        pass

    @abstractmethod
    def score_location(self, rtoken, prev_parts, loc):
        pass

    @abstractmethod
    def sample_token(self, ctype):
        """
        Parameters
        ----------
        ctype : ConceptType

        Returns
        -------
        ctoken : ConceptToken
        """
        assert isinstance(ctype, ConceptType)
        P = []
        R = []
        for p, r in zip(ctype.part_types, ctype.relation_types):
            # sample part token
            ptoken = self.pdist.sample_part_token(p)
            # sample relation token
            rtoken = self.rdist.sample_relation_token(r)
            # sample part position from relation token
            ptoken.position = self.sample_location(rtoken, P)
            # append them to the list
            P.append(ptoken)
            R.append(rtoken)
        ctoken = ConceptToken(P, R)

        return ctoken

    @abstractmethod
    def score_token(self, ctype, ctoken):
        """
        Parameters
        ----------
        ctype : ConceptType
        ctoken : ConceptToken

        Returns
        -------
        ll : tensor
        """
        ll = 0.
        for i in range(ctype.k):
            ll = ll + self.pdist.score_part_token(
                ctype.part_types[i], ctoken.part_tokens[i]
            )
            ll = ll + self.rdist.score_relation_token(
                ctype.relation_types[i], ctoken.relation_tokens[i]
            )
            ll = ll + self.score_location(
                ctoken.relation_tokens[i], ctoken.part_tokens[:i],
                ctoken.part_tokens[i].position
            )

        return ll


class CharacterTokenDist(ConceptTokenDist):
    """
    Defines the distribution P(Token | Type) for characters
    """
    def __init__(self, lib):
        super(CharacterTokenDist, self).__init__(lib)
        self.pdist = StrokeTokenDist(lib)
        self.default_ps = defaultps()

    def sample_location(self, rtoken, prev_parts):
        pass

    def score_location(self, rtoken, prev_parts, loc):
        pass

    def sample_affine(self):
        """
        Sample an affine warp
        TODO: update this function. right now it returns None

        Returns
        -------
        affine : (4,) tensor
            affine transformation
        """
        # set affine to None for now
        affine = None

        return affine

    def score_affine(self, affine):
        return 0.

    def sample_image_noise(self):
        """
        Sample an "epsilon," i.e. image noise quantity
        TODO: update this function. right now it returns fixed quantity

        Returns
        -------
        epsilon : tensor
            scalar; image noise quantity
        """
        # set rendering parameters to minimum noise for now
        epsilon = self.default_ps.min_epsilon

        return epsilon

    def score_image_noise(self, epsilon):
        return 0.

    def sample_image_blur(self):
        """
        Sample a "blur_sigma," i.e. image blur quantity
        TODO: update this function. right now it returns fixed quantity

        Returns
        -------
        blur_sigma: tensor
            scalar; image blur quantity
        """
        # set rendering parameters to minimum noise for now
        blur_sigma = self.default_ps.min_blur_sigma

        return blur_sigma

    def score_image_blur(self, blur_sigma):
        return 0.

    def sample_token(self, ctype):
        """
        Sample a character token from P(Token | Type = type).
        Note: should only be called from Model

        Parameters
        ----------
        ctype : CharacterType
            TODO

        Returns
        -------
        ctoken : CharacterToken
            character token
        """
        # sample part and relation tokens
        concept_token = super(CharacterTokenDist, self).sample_token()

        # sample affine warp
        affine = self.sample_affine() # (4,) tensor

        # sample rendering parameters
        epsilon = self.sample_image_noise()
        blur_sigma = self.sample_image_blur()

        # create the character token
        ctoken = CharacterToken(
            concept_token.part_tokens, concept_token.relation_tokens, affine,
            epsilon, blur_sigma
        )

        return ctoken

    def score_token(self, ctype, ctoken):
        """
        Compute the log-probability of a concept token,
        log P(Token = token | Type = type).
        Note: Should only be called from Model

        Parameters
        ----------
        ctype : CharacterType
            concept type to condition on
        ctoken : CharacterToken
            concept token to be scored

        Returns
        -------
        ll : tensor
            scalar; log-likelihood of the token
        """
        ll = super(CharacterTokenDist, self).score_token(ctype, ctoken)
        ll += self.score_affine(ctoken.affine)
        ll += self.score_image_noise(ctoken.epsilon)
        ll += self.score_image_blur(ctoken.blur_sigma)

        return ll


class PartTokenDist(object):
    __metaclass__ = ABCMeta
    def __init__(self, lib):
        self.lib = lib

    @abstractmethod
    def sample_part_token(self, ptype):
        pass

    @abstractmethod
    def score_part_token(self, ptype, ptoken):
        pass


class StrokeTokenDist(PartTokenDist):
    def __init__(self, lib):
        super(PartTokenDist, self).__init__(lib)

    def sample_shapes_token(self, shapes_type):
        """
        Sample a token of each sub-stroke's shapes

        Parameters
        ----------
        shapes_type : (ncpt, 2, nsub) tensor
            shapes type to condition on

        Returns
        -------
        shapes_token : (ncpt, 2, nsub) tensor
            sampled shapes token
        """
        shapes_dist = dist.normal.Normal(
            shapes_type, self.lib.tokenvar['sigma_shape']
        )
        # sample shapes token
        shapes_token = shapes_dist.sample()

        return shapes_token

    def score_shapes_token(self, shapes_type, shapes_token):
        """
        Compute the log-likelihood of each sub-strokes's shapes

        Parameters
        ----------
        shapes_type : (ncpt, 2, nsub) tensor
            shapes type to condition on
        shapes_token : (ncpt, 2, nsub) tensor
            shapes tokens to score

        Returns
        -------
        ll : (nsub,) tensor
            vector of log-likelihood scores
        """
        shapes_dist = dist.normal.Normal(
            shapes_type, self.lib.tokenvar['sigma_shape']
        )
        # compute scores for every element in shapes_token
        ll = shapes_dist.log_prob(shapes_token)

        return ll

    def sample_invscales_token(self, invscales_type):
        """
        Sample a token of each sub-stroke's scale

        Parameters
        ----------
        invscales_type : (nsub,) tensor
            invscales type to condition on

        Returns
        -------
        invscales_token : (nsub,) tensor
            sampled invscales token
        """
        scales_dist = dist.normal.Normal(
            invscales_type, self.lib.tokenvar['sigma_invscale']
        )
        while True:
            invscales_token = scales_dist.sample()
            ll = self.score_invscales_token(invscales_token)
            if not torch.any(ll == -float('inf')):
                break

        return invscales_token

    def score_invscales_token(self, invscales_type, invscales_token):
        """
        Compute the log-likelihood of each sub-stroke's scale

        Parameters
        ----------
        invscales_type : (nsub,) tensor
            invscales type to condition on
        invscales_token : (nsub,) tensor
            scales tokens to score

        Returns
        -------
        ll : (nsub,) tensor
            vector of log-likelihood scores
        """
        scales_dist = dist.normal.Normal(
            invscales_type, self.lib.tokenvar['sigma_invscale']
        )
        # compute scores for every element in invscales_token
        ll = scales_dist.log_prob(invscales_token)

        # correction for positive only invscales
        p_below = scales_dist.cdf(0.)
        p_above = 1. - p_below
        ll = ll - torch.log(p_above)

        # don't allow invscales that are negative
        out_of_bounds = invscales_token <= 0
        ll[out_of_bounds] = -float('inf')

        return ll

    def sample_part_token(self, ptype):
        """
        Sample a stroke token

        Parameters
        ----------
        ptype : StrokeType
            stroke type to condition on

        Returns
        -------
        ptoken : StrokeToken
            stroke token sample
        """
        shapes_token = self.sample_shapes_token(ptype.shapes)
        invscales_token = self.sample_invscales_token(ptype.invscales)
        ptoken = StrokeToken(shapes_token, invscales_token)

        return ptoken

    def score_part_token(self, ptype, ptoken):
        """
        Compute the log-likelihood of a stroke token

        Parameters
        ----------
        ptype : StrokeType
            stroke type to condition on
        ptoken : StrokeToken
            stroke token to score

        Returns
        -------
        ll : tensor
            scalar; log-likelihood of the stroke token
        """
        shapes_scores = self.score_shapes_token(ptype.invscales, ptoken.shapes)
        invscales_scores = self.score_invscales_token(
            ptype.invscales, ptoken.invscales
        )
        ll = torch.sum(shapes_scores) + torch.sum(invscales_scores)

        return ll


class RelationTokenDist(object):
    __metaclass__ = ABCMeta

    def __init__(self, lib):
        self.lib = lib

    def sample_relation_token(self, rtype):
        """
        TODO
        """
        pass

    def score_relation_token(self, rtype, rtoken):
        """
        TODO
        """
        pass
