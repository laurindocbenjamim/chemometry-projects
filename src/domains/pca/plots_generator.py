import io
import base64
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Enforce headless rendering
import matplotlib.pyplot as plt

def _fig_to_base64(fig) -> str:
    """Converts a Matplotlib figure into a base64 encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_b64

def generate_matplotlib_plots(algo: str, X_orig: np.ndarray, X_processed: np.ndarray, wl: list, sample_names: list, classes: list, extra: dict) -> dict:
    """Generates the original scientific Matplotlib plots as base64 strings."""
    unique_classes = sorted(list(set(classes)))
    # Safe cyclic color map if there are many classes
    color_map = {cls: plt.cm.tab10(i % 10) for i, cls in enumerate(unique_classes)}
    original_images = {}

    # 1. Plot Spectral Lines by Label (All Algorithmic pipelines use this)
    try:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for i in range(len(sample_names)):
            ax.plot(wl, X_processed[i], color=color_map[classes[i]], alpha=0.7)
        from matplotlib.lines import Line2D
        legend_el = [Line2D([0], [0], color=color_map[c], lw=2, label=f"Class {c}") for c in unique_classes]
        ax.legend(handles=legend_el)
        ax.set_title("Spectral Lines by Label (Original Matplotlib)")
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("Intensity")
        fig.tight_layout()
        original_images["spectra"] = _fig_to_base64(fig)
    except Exception:
        pass

    if algo == "PCA":
        _generate_pca_plots(original_images, extra, unique_classes, classes, wl, color_map)
    elif algo == "PLS":
        _generate_pls_plots(original_images, extra, unique_classes, classes, wl, color_map)
    elif algo == "RAMAN":
        _generate_raman_plots(original_images, X_orig, extra, wl, sample_names)

    return original_images

def _generate_pca_plots(images: dict, extra: dict, unique_classes: list, classes: list, wl: list, color_map: dict):
    X_pca = extra.get("X_pca")
    var_ratio = extra.get("var_ratio", [])
    loadings = extra.get("loadings")

    # Scores scatter plot
    try:
        fig, ax = plt.subplots(figsize=(8, 5))
        for cls in unique_classes:
            idx = [i for i, c in enumerate(classes) if c == cls]
            ax.scatter(X_pca[idx, 0], X_pca[idx, 1], label=f"Class {cls}", s=50, color=color_map[cls])
        ax.set_title("PCA Scores Plot")
        ax.set_xlabel("PC 1")
        ax.set_ylabel("PC 2")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.5)
        fig.tight_layout()
        images["scores"] = _fig_to_base64(fig)
    except Exception:
        pass

    # Scree Plot
    try:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(range(1, len(var_ratio) + 1), [v * 100 for v in var_ratio], "o-", linewidth=2, color="blue")
        ax.set_title("Scree Plot")
        ax.set_xlabel("Principal Component")
        ax.set_ylabel("Variance Explained (%)")
        ax.set_xticks(range(1, len(var_ratio) + 1))
        ax.grid(True, linestyle="--", alpha=0.5)
        fig.tight_layout()
        images["scree"] = _fig_to_base64(fig)
    except Exception:
        pass

    # Loadings plot
    try:
        fig, ax = plt.subplots(figsize=(8, 4))
        for i in range(min(2, loadings.shape[1])):
            ax.plot(wl, loadings[:, i], label=f"PC{i+1}")
        ax.set_title("PCA Loadings Line Plot")
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("Loading Value")
        ax.legend()
        fig.tight_layout()
        images["loadings"] = _fig_to_base64(fig)
    except Exception:
        pass

    # T2 vs Q Residuals Plot
    try:
        T2 = extra.get("T2")
        Q = extra.get("Q")
        T2_limit = extra.get("T2_limit", 0)
        Q_limit = extra.get("Q_limit", 0)
        if T2 is not None and Q is not None:
            fig, ax = plt.subplots(figsize=(8, 5))
            for cls in unique_classes:
                idx = [i for i, c in enumerate(classes) if c == cls]
                ax.scatter(T2[idx], Q[idx], label=f"Class {cls}", s=50, color=color_map[cls])
            if T2_limit > 0:
                ax.axvline(x=T2_limit, color="red", linestyle="--", alpha=0.7, label=f"T² 95% limit ({T2_limit:.2f})")
            if Q_limit > 0:
                ax.axhline(y=Q_limit, color="blue", linestyle="--", alpha=0.7, label=f"Q 95% limit ({Q_limit:.2f})")
            ax.set_title("Hotelling's T² vs Q Residuals Plot")
            ax.set_xlabel("Hotelling's T²")
            ax.set_ylabel("Q Residuals")
            ax.legend()
            ax.grid(True, linestyle="--", alpha=0.5)
            fig.tight_layout()
            images["residuals"] = _fig_to_base64(fig)
    except Exception:
        pass

    # PCA Heatmap by class and replicate (legacy feature!)
    try:
        df_scores = pd.DataFrame({"label": classes, "PCA1": X_pca[:, 0]})
        df_scores["replicate"] = df_scores.groupby("label").cumcount() + 1
        B_df = df_scores.pivot(index="replicate", columns="label", values="PCA1")
        fig, ax = plt.subplots(figsize=(8, 5))
        im = ax.imshow(B_df.values, cmap="viridis", aspect="auto")
        ax.set_xticks(np.arange(B_df.shape[1]))
        ax.set_xticklabels(B_df.columns)
        ax.set_yticks(np.arange(B_df.shape[0]))
        ax.set_yticklabels(B_df.index)
        ax.set_xlabel("Class")
        ax.set_ylabel("Replicate")
        fig.colorbar(im, ax=ax, label="PCA1 score")
        ax.set_title("PCA1 Scores by Class and Replicate Heatmap")
        fig.tight_layout()
        images["heatmap"] = _fig_to_base64(fig)
    except Exception:
        pass

def _generate_pls_plots(images: dict, extra: dict, unique_classes: list, classes: list, wl: list, color_map: dict):
    X_pls = extra.get("X_pls")
    loadings = extra.get("loadings")

    try:
        fig, ax = plt.subplots(figsize=(8, 5))
        for cls in unique_classes:
            idx = [i for i, c in enumerate(classes) if c == cls]
            ax.scatter(X_pls[idx, 0], X_pls[idx, 1], label=f"Class {cls}", s=50, color=color_map[cls])
        ax.set_title("PLS-DA Scores Plot")
        ax.set_xlabel("Component 1")
        ax.set_ylabel("Component 2")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.5)
        fig.tight_layout()
        images["scores"] = _fig_to_base64(fig)
    except Exception:
        pass

    try:
        fig, ax = plt.subplots(figsize=(8, 4))
        for i in range(min(2, len(loadings[0]))):
            ax.plot(wl, [l[i] for l in loadings], label=f"Component {i+1}")
        ax.set_title("PLS Loadings Line Plot")
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("Loading Value")
        ax.legend()
        fig.tight_layout()
        images["loadings"] = _fig_to_base64(fig)
    except Exception:
        pass

def _generate_raman_plots(images: dict, X_orig: np.ndarray, extra: dict, wl: list, sample_names: list):
    corrected = extra.get("corrected")
    baselines = extra.get("baselines")

    try:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.plot(wl, X_orig[0], label="Raw Signal", color="gray", alpha=0.8)
        ax.plot(wl, baselines[0], label="ALS Baseline", color="red", linestyle="--")
        ax.plot(wl, corrected[0], label="Corrected Raman", color="blue", linewidth=1.5)
        ax.set_title(f"ALS Baseline Subtraction - Sample: {sample_names[0]}")
        ax.set_xlabel("Raman Shift / Wavelength")
        ax.set_ylabel("Intensity")
        ax.legend()
        fig.tight_layout()
        images["raman"] = _fig_to_base64(fig)
    except Exception:
        pass
