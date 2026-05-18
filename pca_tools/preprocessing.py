import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from scipy.signal import savgol_filter

def calculate_snv(x):
    """
    Standard Normal Variate (SNV) transformation.
    """
    x_mean = np.mean(x, keepdims=True, axis=1)
    x_std = np.std(x, keepdims=True, axis=1)
    x_snv = (x - x_mean) / x_std
    return x_snv

def savitzky_golay_filter(X, window_length=11, polyorder=2, deriv=0):
    """
    Apply Savitzky-Golay filter to the input dataset.
    """
    X = np.asarray(X, dtype=float)

    if window_length % 2 == 0:
        window_length += 1

    if window_length > X.shape[1]:
        window_length = X.shape[1] if X.shape[1] % 2 == 1 else X.shape[1] - 1

    if polyorder >= window_length:
        raise ValueError("polyorder must be smaller than window_length")

    X_sg = savgol_filter(
        X,
        window_length=window_length,
        polyorder=polyorder,
        deriv=deriv,
        axis=1
    )
    return X_sg

def mean_centering(X):
    """
    Perform mean centering on the input dataset.
    """
    variable_means = np.mean(X, axis=0)
    X_centered = X - variable_means
    return X_centered

def baseline_als(y, lam=1e5, p=0.01, niter=10):
    """
    Asymmetric Least Squares (AsLS) baseline correction (Eilers & Boelens, 2005).
    Works on 1D arrays. If y is 2D, fits baseline for each spectrum.
    """
    y = np.asarray(y, dtype=float)
    if y.ndim == 2:
        corrected = np.zeros_like(y)
        baselines = np.zeros_like(y)
        for i in range(y.shape[0]):
            b = _baseline_als_1d(y[i], lam, p, niter)
            baselines[i] = b
            corrected[i] = y[i] - b
        return corrected, baselines
    else:
        b = _baseline_als_1d(y, lam, p, niter)
        return y - b, b

def _baseline_als_1d(y, lam, p, niter):
    L = len(y)
    D = sparse.diags([1, -2, 1], [0, 1, 2], shape=(L-2, L)).tocsc()
    w = np.ones(L)
    for _ in range(niter):
        W = sparse.diags(w, 0, shape=(L, L)).tocsc()
        Z = W + lam * D.T.dot(D)
        z = spsolve(Z, w * y)
        w = p * (y > z) + (1 - p) * (y < z)
    return z
