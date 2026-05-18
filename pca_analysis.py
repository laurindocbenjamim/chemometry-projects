import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA

from pca_tools import (
    load_texas_instruments_data,
    load_sp_data,
    calculate_snv,
    savitzky_golay_filter,
    mean_centering,
    plot_data_classes,
    plot_pca,
    plot_pca_scores_heatmap
)

if __name__ == "__main__":
    # Target directory path for .sp files
    sp_directory = (
        "/home/feti/Documents/PythonProjects/chemometry-projects/test-project/Spectrometria/"
        "Groupe1_BCC_2026-20260518T001605Z-3-001/Groupe1_BCC_2026/Table-Sensor"
    )
    
    # Target directory path for CSV files (fallback/original)
    csv_directory = (
        "/home/feti/Documents/PythonProjects/chemometry-projects/test-project/Spectrometria/"
        "Groupe1_BCC_2026-20260518T001605Z-3-001/Groupe1_BCC_2026/R13-Sensor"
    )

    """# Determine which directory and format to use
    if os.path.exists(sp_directory) and glob.glob(os.path.join(sp_directory, "**/*.sp"), recursive=True):
        data_directory = sp_directory
        file_format = "sp"
    el"""
    if os.path.exists(csv_directory) and glob.glob(os.path.join(csv_directory, "**/*.csv"), recursive=True):
        data_directory = csv_directory
        file_format = "csv"
    else:
        # Fallback to local directory or /content/
        data_directory = '/content/'
        file_format = "csv" if glob.glob(os.path.join(data_directory, "*.csv")) else "sp"

    print(f"Using data directory: {data_directory} (Format: {file_format})")

    # Load data based on file format
    if file_format == "sp":
        df = load_sp_data(data_directory, excel_name='output_excel')
        # Use full name or extract class from subfolders if available
        labels = df['Name'].tolist()
        
        # If all names are 'Administrator XXX', let's use the folder name or numbers to distinguish classes if needed.
        # But we'll fallback to full label which is robust.
        labels = np.array(labels)
        data = df.iloc[:, 1:].to_numpy()
    else:
        df = load_texas_instruments_data(data_directory, skiprows=21, excel_name='output_excel')
        labels = df['Name']
        labels = np.array([label[0] for label in labels])
        data = df.iloc[:, 1:228].to_numpy()

    # Raw plot
    for spectrum in data:
        plt.plot(spectrum, color='black')
    plt.title('Raw Spectra')
    plt.show()

    print("Shape of data:", data.shape)
    print("Shape of labels:", labels.shape)

    # Raw with labels
    plot_data_classes(data, labels)

    def apply_and_plot_pca(data_for_pca, labels, p=2):
        n = data_for_pca.shape[0]
        pca = PCA(n_components=p)
        pca_result = pca.fit_transform(data_for_pca)
        variance_explained = pca.explained_variance_ratio_
        loadings = pca.components_.T
        loadings_df = pd.DataFrame(loadings, columns=[f'PCA{i+1}' for i in range(pca.n_components_)])
        X_reconstructed = pca.inverse_transform(pca_result)

        plot_pca(
            pca_result, variance_explained, loadings, loadings_df, n, p, X_reconstructed, data_for_pca, labels
        )
        return pca_result

    # 1. PCA on Raw Data
    print("--- PCA on Raw Data ---")
    pca_result_raw = apply_and_plot_pca(data, labels)

    # 2. PCA on SNV Filtered Data
    print("--- PCA on SNV Filtered Data ---")
    data_snv = calculate_snv(data)
    plot_data_classes(data_snv, labels)
    pca_result_snv = apply_and_plot_pca(data_snv, labels)

    # 3. PCA on Savitzky-Golay Filtered Data
    print("--- PCA on Savitzky-Golay Filtered Data ---")
    data_sg = savitzky_golay_filter(data_snv, window_length=15, polyorder=2, deriv=0)
    plot_data_classes(data_sg, labels)
    pca_result_sg = apply_and_plot_pca(data_sg, labels)

    # 4. PCA on Mean Centered Data
    print("--- PCA on Mean Centered Data ---")
    data_mc = mean_centering(data_sg)
    plot_data_classes(data_mc, labels)
    pca_result_mc = apply_and_plot_pca(data_mc, labels)
    
    # 5. Plot Heatmap for the last PCA result
    print("--- PCA Scores Heatmap ---")
    plot_pca_scores_heatmap(pca_result_mc, labels)
