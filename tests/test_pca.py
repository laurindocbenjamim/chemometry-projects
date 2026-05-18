import numpy as np
import pytest
from scipy import sparse
from sklearn.decomposition import PCA
from sklearn.cross_decomposition import PLSRegression

# Import functions to test (we will define them in our modular package)
from pca_tools.preprocessing import calculate_snv, savitzky_golay_filter, mean_centering
from pca_tools.sp_reader import read_sp

# Manual implementation of ALS for testing
def baseline_als(y, lam=1e5, p=0.01, niter=10):
    L = len(y)
    # Correct sparse matrix constructor for second derivative difference
    # Let's create a sparse second derivative operator D
    D = sparse.diags([1, -2, 1], [0, 1, 2], shape=(L-2, L)).tocsc()
    w = np.ones(L)
    for i in range(niter):
        W = sparse.diags(w, 0, shape=(L, L)).tocsc()
        Z = W + lam * D.T.dot(D)
        z = sparse.linalg.spsolve(Z, w * y)
        w = p * (y > z) + (1 - p) * (y < z)
    return z

def test_snv_transformation():
    """Test that SNV transforms data to mean=0 and std=1 across variables."""
    dummy_data = np.random.rand(5, 100) * 100 + 50
    snv_data = calculate_snv(dummy_data)
    
    assert snv_data.shape == dummy_data.shape
    np.testing.assert_array_almost_equal(np.mean(snv_data, axis=1), np.zeros(5), decimal=5)
    np.testing.assert_array_almost_equal(np.std(snv_data, axis=1), np.ones(5), decimal=5)

def test_savitzky_golay_filter():
    """Test that Savitzky-Golay filter shape matches input."""
    dummy_data = np.random.rand(5, 100)
    filtered = savitzky_golay_filter(dummy_data, window_length=11, polyorder=2)
    assert filtered.shape == dummy_data.shape

def test_mean_centering():
    """Test that mean centering forces mean of each variable to 0."""
    dummy_data = np.random.rand(10, 50)
    centered = mean_centering(dummy_data)
    
    assert centered.shape == dummy_data.shape
    np.testing.assert_array_almost_equal(np.mean(centered, axis=0), np.zeros(50), decimal=5)

def test_als_baseline_correction():
    """Test that ALS baseline correction removes trend and leaves signal flat."""
    x = np.linspace(0, 10, 100)
    baseline = 2.0 * x + 5.0
    signal = np.sin(x)
    y = baseline + signal
    
    corrected_baseline = baseline_als(y, lam=1e5, p=0.05)
    corrected_signal = y - corrected_baseline
    
    # Corrected signal should be close to sin(x) plus small offset, check correlation
    correlation = np.corrcoef(signal, corrected_signal)[0, 1]
    assert correlation > 0.9  # Should be highly correlated to true signal

def test_pls_discriminant_analysis():
    """Test PLS-DA projection shape and fitting."""
    X = np.random.rand(15, 30)
    # 2 classes: 0 and 1
    y_labels = np.array([0]*7 + [1]*8)
    
    # PLS model fitting
    pls = PLSRegression(n_components=2)
    pls.fit(X, y_labels)
    
    X_scores = pls.x_scores_
    assert X_scores.shape == (15, 2)
