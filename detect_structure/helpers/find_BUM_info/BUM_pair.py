from __future__ import annotations
import logging
from typing import Literal

logger = logging.getLogger(__name__)

class Pair:

    def __init__(self, bound_1: float, bound_2: float) -> None:

        self.incomplete = False
        self.top_pair = False
        self.bottom_pair = False
        self.might_extend_more = False
        self.imaginary = False
        
        self.top_bound = min(bound_1, bound_2)
        self.low_bound = max(bound_1, bound_2)
        self.span = self.low_bound - self.top_bound
    
    def __str__(self) -> str:
        ret = f'[{self.top_bound} : {self.low_bound}'
        if self.incomplete:
            ret += ', incomplete'
        if self.top_pair:
            ret += ', top pair'
        if self.bottom_pair:
            ret += ', bottom pair'
        if self.might_extend_more:
            ret += ', might extend more'
        ret += ']'
        return ret

    def __repr__(self) -> str:
        return self.__str__()
        
    @staticmethod
    def find_bum_pairs(init_bounds: list[float], top: float, bottom: float, try_again=True) -> list[Pair] | Literal[False]:
        """
        Look for BUM pairs that can be created through bounds. If a pair can't
        be created by a bound, it is ignored and this function is recursively
        run until all bounds are consumed.
        """

        bounds: list[float] = sorted(init_bounds)
        pairs: list[Pair] = []

        if len(bounds) == 1:
            # Special case: there is only one bound

            # Check to see whether it's bottom or top
            if bottom - bounds[0] <= 1.0:
                p = Pair(bounds[0], bottom)
                p.bottom_pair = True
                pairs.append(p)
            elif bounds[0] - top <= 1.0:
                p = Pair(bounds[0], top)
                p.top_pair = True
                pairs.append(p)
            else:
                logger.warning('Had one bound, but could not match it with top or bottom')
                return False
        
        
        elif len(bounds) > 1:
            # Normal case, more than one bound is present

            # First test last pair
            if bounds[-1] - bounds[-2] <= 1.0:
                # Last two connect to form pair
                p = Pair(bounds[-1], bounds[-2])
                if p.span == 0.5:
                    logger.debug('The last pair might extend more')
                    p.might_extend_more = True
                pairs.append(p)
                bounds = bounds[:-2]

            elif bottom - bounds[-1] <= 1.0:
                # Last bound connects to bottom to form pair
                
                p = Pair(bounds[-1], bottom)
                p.bottom_pair = True
                pairs.append(p)
                bounds = bounds[:-1]

            else:
                # Last bound doesn't connect to anything
                
                logger.warning('Could not match bottommost bound')
                logger.warning(f'init_bounds: {init_bounds}')
                logger.warning('Creating a made up one')

                p = Pair(bounds[-1], bounds[-1]+0.5)
                p.imaginary = True
                pairs.append(p)
                bounds = bounds[:-1]

                # if not try_again:
                #     return False

                # # Try again but ignore this last bound
                # logger.warning('Running an alternate to see if viable without')
                # ret = Pair.find_bum_pairs(init_bounds[:-1], top, bottom, try_again=False)
                # if not ret:
                #     if len(bounds) - 2 >= 1:
                #         # Try again, but ignore the last 2 bounds
                #         return Pair.find_bum_pairs(init_bounds[:-2], top, bottom, try_again=False)
                #     else:
                #         # There aren't enough bounds to try again
                #         return False
                # else:
                #     return ret

            # Work our way down
            while len(bounds) >= 2:
                b_1 = bounds[-1]
                b_2 = bounds[-2]
                p = Pair._handle_pair(b_1, b_2)
                if p:
                    pairs.append(p)
                    bounds = bounds[:-2]
                else:
                    # The boundary couldn't be matched, try passing things down
                    t = Pair.find_bum_pairs(bounds[:-1], top, bottom, try_again=False)
                    bounds = []
                    if t:
                        pairs += t
                        
            
            # Take care of the last bound, which should be the first pair
            if len(bounds) == 1:

                if bounds[0] - top > 1.0:
                    logger.debug('Exception')
                    logger.debug('init_bounds:', init_bounds)
                    logger.warning('Could not match last BUM boundary with top')
                else:
                    p = Pair(bounds[0], top)
                    p.top_pair = True
                    pairs.append(p)
        else:
            logger.warning('find_bum_pairs called with empty array')
            return False

        logger.debug(f'Found {len(pairs)} pairs')
        logger.debug(pairs)
        return pairs

    @staticmethod
    def _handle_pair(b1: float, b2: float) -> Pair | Literal[False]:

        logger.debug(f'Handling pair {[b1, b2]}')

        if b1 - b2 == 0.5:
            logger.debug(f'Found a pair that might extend more')
            p = Pair(b1, b2)
            p.might_extend_more = True
            return p

        elif b1 - b2 == 1.0:
            return Pair(b1, b2)

        else:
            logger.warning('Could not match BUM boundary with next in list')
            return False