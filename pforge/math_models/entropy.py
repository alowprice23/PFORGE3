from __future__ import annotations
from typing import List, Dict
import math
import numpy as np
from collections import Counter

def style_entropy(style_vectors: np.ndarray) -> float:
    """
    Calculates the style entropy based on the Mahalanobis distance.
    This requires a baseline of "good" style vectors to compare against.
    Placeholder: returns the mean variance of the vectors.
    """
    if style_vectors.size == 0:
        return 0.0
    # A real implementation would use Mahalanobis distance from a centroid.
    # For now, we use a simpler proxy: mean variance across features.
    return np.mean(np.var(style_vectors, axis=0))

def structural_entropy(dependency_graph: Dict[str, List[str]]) -> float:
    """
    Calculates the structural entropy of the dependency graph.
    Uses Shannon entropy of the degree distribution.
    """
    if not dependency_graph:
        return 0.0

    degrees = [len(deps) for deps in dependency_graph.values()]
    total_degrees = sum(degrees)
    if total_degrees == 0:
        return 0.0

    degree_counts = Counter(degrees)
    entropy = 0.0
    for count in degree_counts.values():
        prob = count / len(degrees)
        entropy -= prob * math.log2(prob)

    return entropy

def process_entropy(pass_rates: List[float], log_noise: float, alpha: float = 0.7) -> float:
    """
    Calculates the process entropy from test flakiness and log noise.
    """
    # Flakiness entropy (Bernoulli entropy for each test)
    flakiness_entropy = 0.0
    if pass_rates:
        for p in pass_rates:
            if 0 < p < 1:
                flakiness_entropy -= (p * math.log2(p) + (1 - p) * math.log2(1 - p))
        flakiness_entropy /= len(pass_rates)

    # Combine with log noise
    return alpha * flakiness_entropy + (1 - alpha) * log_noise
