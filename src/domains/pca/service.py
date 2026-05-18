import io
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.cross_decomposition import PLSRegression

from pca_tools.sp_reader import read_sp_from_bytes
from pca_tools.preprocessing import calculate_snv, savitzky_golay_filter, mean_centering, baseline_als
from src.domains.pca.schemas import PipelineRequest

def detect_file_format(content: bytes) -> str:
    """Detects if the file is a PerkinElmer .sp file or a TI CSV file."""
    if len(content) >= 4 and content[:4] == b'PEPE':
        return "sp"
    
    # Try decoding as text to check if it's a CSV
    try:
        header = content[:1024].decode("cp1252", errors="ignore")
        if "Wavelength" in header or "Absorbance" in header or "Sample Signal" in header:
            return "csv"
    except Exception:
        pass
    
    raise ValueError("Unsupported file format. Files must be valid PerkinElmer .sp or Texas Instruments CSVs.")

def parse_file_to_spectrum(content: bytes, filename: str, expected_format: str) -> tuple:
    """Parses a file content into (spectrum, wavelengths, sample_name)."""
    detected = detect_file_format(content)
    if expected_format != "auto" and detected != expected_format:
        raise ValueError(f"File {filename} detected as {detected}, but requested {expected_format}.")
    
    if detected == "sp":
        return read_sp_from_bytes(content, filename)
    else:
        text_data = content.decode("cp1252", errors="ignore")
        df_aux = pd.read_csv(io.StringIO(text_data), skiprows=21)
        absorbance_col = next((c for c in df_aux.columns if "Absorbance" in c), None)
        if absorbance_col is None:
            raise KeyError(f"Absorbance column not found in CSV {filename}")
        
        spectrum = df_aux[absorbance_col].to_numpy()
        wavelengths = df_aux["Wavelength (nm)"].to_numpy()
        name = filename.replace(".csv", "")
        return spectrum, wavelengths, {"filename": filename, "name": name}

def process_spectroscopy_pipeline(files: list, request: PipelineRequest) -> dict:
    """Core logic to process uploaded files, perform preprocessing and run selected algorithm."""
    parsed_spectra = []
    parsed_wavelengths = []
    sample_names = []
    
    # 1. Parse all files and validate formats/wavelength alignment
    detected_format = None
    for filename, content in files:
        if not detected_format:
            detected_format = detect_file_format(content)
            # If user explicitly requested format, validate it
            if request.format != "auto" and detected_format != request.format:
                raise ValueError(f"Uploaded files are in {detected_format} format, but {request.format} was requested.")
        
        spectrum, wl, meta = parse_file_to_spectrum(content, filename, detected_format)
        parsed_spectra.append(spectrum)
        parsed_wavelengths.append(wl)
        sample_names.append(meta.get("name", filename))

    if not parsed_spectra:
        raise ValueError("No valid spectra files could be parsed.")

    # Validate that all files have identical wavelength grids
    base_wl = parsed_wavelengths[0]
    for i, wl in enumerate(parsed_wavelengths[1:]):
        if len(wl) != len(base_wl) or not np.allclose(wl, base_wl, atol=1e-2):
            raise ValueError(f"Wavelength misalignment: File '{sample_names[i+1]}' has a different wavelength grid.")

    X = np.array(parsed_spectra, dtype=float)
    wl_list = base_wl.tolist()
    
    # Extract default classes using the first letter of sample names
    classes = [name[0].upper() for name in sample_names]
    
    # 2. Apply Preprocessing Pipeline
    X_processed = X.copy()
    if request.preprocessing.snv:
        X_processed = calculate_snv(X_processed)
    if request.preprocessing.sg_filter:
        X_processed = savitzky_golay_filter(
            X_processed,
            window_length=request.preprocessing.sg_window_length,
            polyorder=request.preprocessing.sg_polyorder,
            deriv=request.preprocessing.sg_deriv
        )
    if request.preprocessing.mean_center:
        X_processed = mean_centering(X_processed)

    plots = {}
    
    # 3. Run selected Algorithm
    algo = request.algorithm.upper()
    if algo == "PCA":
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_processed)
        var_ratio = pca.explained_variance_ratio_.tolist()
        loadings = pca.components_.T.tolist()
        
        # Calculate Hotelling's T^2 and Q Residuals
        # T^2 = sum_i(t_i^2 / lambda_i)
        eigenvalues = pca.explained_variance_
        T2 = np.sum((X_pca ** 2) / eigenvalues, axis=1).tolist()
        
        # Q residuals = ||X - X_reconstructed||^2
        X_reconstructed = pca.inverse_transform(X_pca)
        Q = np.sum((X_processed - X_reconstructed) ** 2, axis=1).tolist()

        plots = {
            "scree": {"labels": ["PC1", "PC2"], "variance": var_ratio},
            "scores": [{"name": sample_names[i], "class": classes[i], "pc1": X_pca[i, 0], "pc2": X_pca[i, 1]} for i in range(len(sample_names))],
            "loadings": {"wavelengths": wl_list, "pc1": [l[0] for l in loadings], "pc2": [l[1] for l in loadings]},
            "residuals": [{"name": sample_names[i], "class": classes[i], "t2": T2[i], "q": Q[i]} for i in range(len(sample_names))]
        }
    
    elif algo == "PLS":
        unique_classes = sorted(list(set(classes)))
        if len(unique_classes) < 2:
            raise ValueError("PLS is a supervised algorithm and requires at least 2 distinct classes (based on the first character of filenames, e.g. 'A1...' and 'B1...').")
        
        class_to_idx = {c: i for i, c in enumerate(unique_classes)}
        Y = np.array([class_to_idx[c] for c in classes], dtype=float)
        
        pls = PLSRegression(n_components=2)
        pls.fit(X_processed, Y)
        X_pls = pls.x_scores_
        loadings = pls.x_loadings_.tolist()
        r2 = float(pls.score(X_processed, Y))

        plots = {
            "scores": [{"name": sample_names[i], "class": classes[i], "comp1": X_pls[i, 0], "comp2": X_pls[i, 1]} for i in range(len(sample_names))],
            "loadings": {"wavelengths": wl_list, "comp1": [l[0] for l in loadings], "comp2": [l[1] for l in loadings]},
            "r2": r2
        }
        
    elif algo == "RAMAN":
        # RAMAN Baseline subtraction via ALS
        corrected, baselines = baseline_als(X, lam=1e5, p=0.01)
        
        plots = {
            "wavelengths": wl_list,
            "samples": [
                {
                    "name": sample_names[i],
                    "class": classes[i],
                    "raw": X[i].tolist(),
                    "corrected": corrected[i].tolist(),
                    "baseline": baselines[i].tolist()
                } for i in range(len(sample_names))
            ]
        }

    return {
        "success": True,
        "algorithm": algo,
        "detected_format": detected_format,
        "samples_count": len(sample_names),
        "wavelengths_count": len(wl_list),
        "plots": plots
    }
