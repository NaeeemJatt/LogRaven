"""Algorithm R Reservoir Sampler (FR-MOD8-01, TC-MOD8-002).

Statistically bounded reservoir sampling selecting exactly k = 200 items from
a stream of N items with uniform probability (k/N) and O(k) memory overhead.
"""

import random
from typing import Any, Iterable, List, Optional, TypeVar

T = TypeVar("T")


class ReservoirSampler:
    """Implements Algorithm R for fixed-memory statistical stream sampling."""

    def __init__(self, k: int = 200, seed: Optional[int] = 42):
        self.k = k
        if seed is not None:
            random.seed(seed)

    def sample(self, items: Iterable[T]) -> List[T]:
        """Samples up to k items from a sequence or generator with uniform distribution."""
        reservoir: List[T] = []

        for i, item in enumerate(items):
            if i < self.k:
                reservoir.append(item)
            else:
                # For i >= k, pick random j in [0, i]
                j = random.randint(0, i)
                if j < self.k:
                    reservoir[j] = item

        return reservoir
