from typing import Callable, Sequence

import numba as nb
import numpy as np


@nb.njit
def _resample(a: np.ndarray) -> np.ndarray:
    """
    Numba implementation of jackknife resampling.
    """
    n = a.shape[0]
    x = np.empty((n - 1, *a.shape[1:]), dtype=a.dtype)
    for i in range(n - 1):
        x[i] = a[1 + i]
    # yield x0
    yield x.view(x.dtype)  # must return view to avoid a numba life-time bug

    # update of x needs to change values only up to i
    # for a = [0, 1, 2, 3]
    # x0 = [1, 2, 3] (yielded above)
    # x1 = [0, 2, 3]
    # x2 = [0, 1, 3]
    # x3 = [0, 1, 2]
    for i in range(1, n):
        for j in range(i):
            x[j] = a[j]
        yield x.view(x.dtype)  # must return view to avoid a numba life-time bug


def resample(a: Sequence) -> np.ndarray:
    """
    Generator of jackknife'd samples.

    Parameters
    ----------
    a: array-like
        Sample. Must be at least one-dimensional and the first dimension must walk over
        the iid observations.

    Yields
    ------
    array with same shape and type as input, but with the size of the first dimension
    reduced by one.

    Notes
    -----
    To increase performance we update the resampled array on each iteration *in place*.
    To store resampled arrays somewhere (not recommended), one has to make copies
    explicitly, e.g.:

    ```
    r = []
    for x in resample(a):
        r.append(x.copy())
    ```
    """
    return _resample(np.atleast_1d(a))


def jackknife(a: np.ndarray, f: Callable) -> np.ndarray:
    """
    Calculate jackknife estimates for a given sample and estimator.

    The jackknife is a linear approximation to the bootstrap. In contrast to the
    bootstrap it is deterministic and does not use random numbers. The caveat is the
    computational cost of the jackknife, which is O(n²) for n observations, compared
    to O(n x k) for k bootstrap replicates. For large samples, the bootstrap is more
    efficient.

    Parameters
    ----------
    a : array-like
        Sample. Must be one-dimensional.

    f : callable
        Estimator. Can be any mapping ℝⁿ → ℝᵏ, where n is the sample size
        and k is the length of the output array.

    Returns
    -------
    np.ndarray
        Jackknife samples.
    """
    return np.asarray([f(x) for x in resample(a)])


def bias(a: Sequence, f: Callable) -> np.ndarray:
    """
    Calculate jackknife estimate of bias.

    The bias estimate is accurate to O(1/n), where n is the number of samples.
    If the bias is exactly O(1/n), then the estimate is exact.

    Wikipedia:
    https://en.wikipedia.org/wiki/Jackknife_resampling

    Parameters
    ----------
    a : array-like
        Sample. Must be one-dimensional.

    f : callable
        Estimator. Can be any mapping ℝⁿ → ℝᵏ, where n is the sample size
        and k is the length of the output array.

    Returns
    -------
    np.ndarray
        Jackknife estimate of bias.
    """
    mj = np.mean(jackknife(a, f), axis=0)
    return (len(a) - 1) * (mj - f(a))


def bias_corrected(a: Sequence, f: Callable) -> np.ndarray:
    """
    Calculates bias-corrected estimate of the function with the jackknife.

    Removes a bias of O(1/n), where n is the sample size, leaving bias of
    order O(1/n²). If the original function has a bias of exactly O(1/n),
    the corrected result is now unbiased.

    Wikipedia:
    https://en.wikipedia.org/wiki/Jackknife_resampling

    Parameters
    ----------
    a : array-like
        Sample. Must be one-dimensional.

    f : callable
        Estimator. Can be any mapping ℝⁿ → ℝᵏ, where n is the sample size
        and k is the length of the output array.

    Returns
    -------
    np.ndarray
        Estimate with O(1/n) bias removed.
    """
    mj = np.mean(jackknife(a, f), axis=0)
    n = len(a)
    return n * f(a) - (n - 1) * mj


def variance(a: Sequence, f: Callable) -> np.ndarray:
    """
    Calculate jackknife estimate of variance.

    Wikipedia:
    https://en.wikipedia.org/wiki/Jackknife_resampling

    Parameters
    ----------
    a : array-like
        Sample. Must be one-dimensional.

    f : callable
        Estimator. Can be any mapping ℝⁿ → ℝᵏ, where n is the sample size
        and k is the length of the output array.

    Returns
    -------
    np.ndarray
        Jackknife estimate of variance.
    """
    # formula is (n - 1) / n * sum((fj - mean(fj)) ** 2)
    #   = np.var(fj, ddof=0) * (n - 1)
    fj = jackknife(a, f)
    return (len(a) - 1) * np.var(fj, ddof=0, axis=0)


def empirical_influence(a: Sequence, f: Callable) -> np.ndarray:
    """
    Calculate the empirical influence function for a given sample and estimator
    using the jackknife method.

    Parameters
    ----------
    a : array-like
        Sample. Must be one-dimensional.

    f : callable
        Estimator. Can be any mapping ℝⁿ → ℝᵏ, where n is the sample size
        and k is the length of the output array.

    Returns
    -------
    np.ndarray
        Empirical influence values.
    """
    return (len(a) - 1) * (f(a) - jackknife(a, f))
