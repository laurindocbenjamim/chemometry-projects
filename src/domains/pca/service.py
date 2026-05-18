import io
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.cross_decomposition import PLSRegression

from pca_tools.sp_reader import read_sp_from_bytes
from pca_tools.preprocessing import calculate_snv, savitzky_golay_filter, mean_centering, baseline_als
from src.domains.pca.schemas import PipelineRequest
from src.domains.pca.plots_generator import generate_matplotlib_plots

def detect_file_format(content: bytes) -> str:
    """Detects if the file is a PerkinElmer .sp file or a TI CSV file."""
    if len(content) >= 4 and content[:4] == b'PEPE':
        return "sp"
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
        return df_aux[absorbance_col].to_numpy(), df_aux["Wavelength (nm)"].to_numpy(), {"name": filename.replace(".csv", "")}

def run_pca_stage(X_orig: np.ndarray, X_stage: np.ndarray, wl_list: list, sample_names: list, classes: list) -> dict:
    """Utility to run PCA projection and compile ApexCharts + Matplotlib plot sets for a stage."""
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_stage)
    var_ratio = pca.explained_variance_ratio_.tolist()
    loadings = pca.components_.T
    eigenvalues = pca.explained_variance_
    T2_arr = np.sum((X_pca ** 2) / eigenvalues, axis=1)
    X_recon = pca.inverse_transform(X_pca)
    Q_arr = np.sum((X_stage - X_recon) ** 2, axis=1)

    # Calculate exact control limits matching the original research script
    n = X_stage.shape[0]
    p = 2
    from scipy.stats import f as f_dist
    alpha = 0.05
    try:
        F_critical = f_dist.ppf(1 - alpha, p, n - p)
        T2_limit = (n - 1) * p / (n - p) * F_critical
    except Exception:
        T2_limit = 0.0
    Q_limit = float(np.percentile(Q_arr, 95))

    plots = {
        "scree": {"labels": ["PC1", "PC2"], "variance": var_ratio},
        "scores": [{"name": sample_names[i], "class": classes[i], "pc1": X_pca[i, 0], "pc2": X_pca[i, 1]} for i in range(len(sample_names))],
        "loadings": {"wavelengths": wl_list, "pc1": loadings[:, 0].tolist(), "pc2": loadings[:, 1].tolist()},
        "residuals": [{"name": sample_names[i], "class": classes[i], "t2": float(T2_arr[i]), "q": float(Q_arr[i])} for i in range(len(sample_names))]
    }
    extra = {
        "X_pca": X_pca,
        "var_ratio": var_ratio,
        "loadings": loadings,
        "T2": T2_arr,
        "Q": Q_arr,
        "T2_limit": T2_limit,
        "Q_limit": Q_limit
    }
    orig_plots = generate_matplotlib_plots("PCA", X_orig, X_stage, wl_list, sample_names, classes, extra)
    return {"plots": plots, "original_plots": orig_plots}

def process_spectroscopy_pipeline(files: list, request: PipelineRequest) -> dict:
    """Core logic to process uploaded files, perform preprocessing and run selected algorithm."""
    parsed_spectra, parsed_wavelengths, sample_names = [], [], []
    detected_format = None
    for filename, content in files:
        if not detected_format:
            detected_format = detect_file_format(content)
            if request.format != "auto" and detected_format != request.format:
                raise ValueError(f"Uploaded files are in {detected_format} format, but {request.format} was requested.")
        spectrum, wl, meta = parse_file_to_spectrum(content, filename, detected_format)
        parsed_spectra.append(spectrum)
        parsed_wavelengths.append(wl)
        sample_names.append(meta.get("name", filename))

    if not parsed_spectra:
        raise ValueError("No valid spectra files could be parsed.")
    base_wl = parsed_wavelengths[0]
    for i, wl in enumerate(parsed_wavelengths[1:]):
        if len(wl) != len(base_wl) or not np.allclose(wl, base_wl, atol=1e-2):
            raise ValueError(f"Wavelength misalignment in file '{sample_names[i+1]}'.")

    X = np.array(parsed_spectra, dtype=float)
    wl_list = base_wl.tolist()
    classes = [name[0].upper() for name in sample_names]
    algo = request.algorithm.upper()

    if algo == "PCA":
        stages, active_stages = {}, ["raw"]
        stages["raw"] = run_pca_stage(X, X, wl_list, sample_names, classes)
        
        X_curr = X.copy()
        if request.preprocessing.snv:
            X_curr = calculate_snv(X_curr)
            stages["snv"] = run_pca_stage(X, X_curr, wl_list, sample_names, classes)
            active_stages.append("snv")
        if request.preprocessing.sg_filter:
            X_curr = savitzky_golay_filter(X_curr, request.preprocessing.sg_window_length, request.preprocessing.sg_polyorder, request.preprocessing.sg_deriv)
            stages["sg"] = run_pca_stage(X, X_curr, wl_list, sample_names, classes)
            active_stages.append("sg")
        if request.preprocessing.mean_center:
            X_curr = mean_centering(X_curr)
            stages["mc"] = run_pca_stage(X, X_curr, wl_list, sample_names, classes)
            active_stages.append("mc")

        return {
            "success": True, "algorithm": algo, "detected_format": detected_format,
            "samples_count": len(sample_names), "wavelengths_count": len(wl_list),
            "plots": {"multi_stage": True, "stages": stages, "active_stages": active_stages}
        }

    elif algo == "PLS":
        unique_classes = sorted(list(set(classes)))
        if len(unique_classes) < 2:
            raise ValueError("PLS requires at least 2 distinct classes (based on the first character of filenames).")
        
        class_to_idx = {c: i for i, c in enumerate(unique_classes)}
        Y = np.array([class_to_idx[c] for c in classes], dtype=float)
        
        # Preprocessing final states
        X_curr = X.copy()
        if request.preprocessing.snv: X_curr = calculate_snv(X_curr)
        if request.preprocessing.sg_filter: X_curr = savitzky_golay_filter(X_curr, request.preprocessing.sg_window_length, request.preprocessing.sg_polyorder, request.preprocessing.sg_deriv)
        if request.preprocessing.mean_center: X_curr = mean_centering(X_curr)

        pls = PLSRegression(n_components=2)
        pls.fit(X_curr, Y)
        X_pls = pls.x_scores_
        loadings = pls.x_loadings_.tolist()
        r2 = float(pls.score(X_curr, Y))

        pls_plots = {
            "scores": [{"name": sample_names[i], "class": classes[i], "comp1": X_pls[i, 0], "comp2": X_pls[i, 1]} for i in range(len(sample_names))],
            "loadings": {"wavelengths": wl_list, "comp1": [l[0] for l in loadings], "comp2": [l[1] for l in loadings]},
            "r2": r2
        }
        extra_data = {"X_pls": X_pls, "loadings": loadings}
        orig_plots = generate_matplotlib_plots("PLS", X, X_curr, wl_list, sample_names, classes, extra_data)
        return {
            "success": True, "algorithm": algo, "detected_format": detected_format,
            "samples_count": len(sample_names), "wavelengths_count": len(wl_list),
            "plots": {"multi_stage": False, "stage": "pls", "plots": pls_plots, "original_plots": orig_plots}
        }

    elif algo == "RAMAN":
        corrected, baselines = baseline_als(X, lam=1e5, p=0.01)
        raman_plots = {
            "wavelengths": wl_list,
            "samples": [{"name": sample_names[i], "class": classes[i], "raw": X[i].tolist(), "corrected": corrected[i].tolist(), "baseline": baselines[i].tolist()} for i in range(len(sample_names))]
        }
        extra_data = {"corrected": corrected, "baselines": baselines}
        orig_plots = generate_matplotlib_plots("RAMAN", X, X, wl_list, sample_names, classes, extra_data)
        return {
            "success": True, "algorithm": algo, "detected_format": detected_format,
            "samples_count": len(sample_names), "wavelengths_count": len(wl_list),
            "plots": {"multi_stage": False, "stage": "raman", "plots": raman_plots, "original_plots": orig_plots}
        }
