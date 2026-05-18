import numpy as np
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

    Args:
        X (np.ndarray): Input dataset of shape (num_samples, num_variables).
                        Rows = samples, columns = variables/wavelengths.
        window_length (int): Length of the filter window. Must be odd.
        polyorder (int): Polynomial order. Must be smaller than window_length.
        deriv (int): Derivative order.
                     0 = smoothing
                     1 = first derivative
                     2 = second derivative

    Returns:
        X_sg (np.ndarray): Savitzky-Golay filtered dataset.
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

    Args:
    X (np.ndarray): Input dataset of shape (num_samples, num_variables).

    Returns:
    X_centered (np.ndarray): Mean-centered dataset.
    """
    variable_means = np.mean(X, axis=0)
    X_centered = X - variable_means
    return X_centered
