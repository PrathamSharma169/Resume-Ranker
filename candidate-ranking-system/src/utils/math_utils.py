"""
Math Utilities
Statistical normalization and mathematical helper functions.
"""

import numpy as np
from typing import Optional


def robust_normalize(values: np.ndarray) -> np.ndarray:
    """Robust normalization using median and IQR (resistant to outliers)."""
    if len(values) == 0:
        return values
    median = np.median(values)
    q1, q3 = np.percentile(values, [25, 75])
    iqr = q3 - q1
    if iqr == 0:
        return np.zeros_like(values)
    return (values - median) / iqr


def minmax_normalize(values: np.ndarray) -> np.ndarray:
    """Min-max normalization to [0, 1] range."""
    if len(values) == 0:
        return values
    vmin, vmax = values.min(), values.max()
    if vmax == vmin:
        return np.zeros_like(values)
    return (values - vmin) / (vmax - vmin)


def standard_normalize(values: np.ndarray) -> np.ndarray:
    """Standard (z-score) normalization."""
    if len(values) == 0:
        return values
    mean = values.mean()
    std = values.std()
    if std == 0:
        return np.zeros_like(values)
    return (values - mean) / std


def normalize(values: np.ndarray, strategy: str = "robust") -> np.ndarray:
    """Normalize values using the specified strategy."""
    strategies = {
        "robust": robust_normalize,
        "minmax": minmax_normalize,
        "standard": standard_normalize,
    }
    func = strategies.get(strategy, robust_normalize)
    return func(values)


def sigmoid(x: float) -> float:
    """Sigmoid function mapping any value to (0, 1)."""
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division that returns default on zero denominator."""
    if denominator == 0:
        return default
    return numerator / denominator


def percentile_rank(value: float, distribution: np.ndarray) -> float:
    """Compute percentile rank of a value within a distribution."""
    if len(distribution) == 0:
        return 0.5
    return float(np.mean(distribution <= value))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def weighted_average(values: list[float], weights: list[float]) -> float:
    """Compute weighted average, handling empty/zero cases."""
    if not values or not weights:
        return 0.0
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    return sum(v * w for v, w in zip(values, weights)) / total_weight


def clip_score(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clip a score to the specified range."""
    return max(low, min(high, value))


class RunningStatistics:
    """Online computation of mean, variance, min, max for streaming data."""

    def __init__(self):
        self.n = 0
        self.mean = 0.0
        self.M2 = 0.0  # sum of squared deviations
        self.min_val = float("inf")
        self.max_val = float("-inf")
        self._values: list[float] = []  # store for percentile computation

    def update(self, value: float) -> None:
        """Update statistics with a new value (Welford's algorithm)."""
        self.n += 1
        delta = value - self.mean
        self.mean += delta / self.n
        delta2 = value - self.mean
        self.M2 += delta * delta2
        self.min_val = min(self.min_val, value)
        self.max_val = max(self.max_val, value)
        self._values.append(value)

    @property
    def variance(self) -> float:
        if self.n < 2:
            return 0.0
        return self.M2 / (self.n - 1)

    @property
    def std(self) -> float:
        return self.variance ** 0.5

    def percentile(self, p: float) -> float:
        """Compute percentile (requires stored values)."""
        if not self._values:
            return 0.0
        return float(np.percentile(self._values, p))

    def z_score(self, value: float) -> float:
        """Compute z-score of a value."""
        if self.std == 0:
            return 0.0
        return (value - self.mean) / self.std
