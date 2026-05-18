import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import matplotlib.colors as mcolors
import seaborn as sns
from scipy.stats import f

def plot_data_classes(data, labels):
    unique_labels = np.unique(labels)
    colors = plt.cm.jet(np.linspace(0, 1, len(unique_labels)))

    label_color_map = {label: color for label, color in zip(unique_labels, colors)}

    legend_lines = []
    legend_labels = []

    for label in unique_labels:
        spectra = data[labels == label]
        color = label_color_map[label]

        for spectrum in spectra:
            line, = plt.plot(spectrum, color=color)

        if label not in legend_labels:
            legend_lines.append(line)
            legend_labels.append(label)

    plt.title('Spectral Lines by Label')
    plt.xlabel('Wavelength Index')
    plt.ylabel('Intensity')
    plt.legend(legend_lines, legend_labels)
    plt.show()

def plot_pca(pca_result, variance_explained, loadings, loadings_df, n, p, X_reconstructed, data_for_pca, labels):
    # Create a DataFrame with the PCA results and the labels for coloring
    pca_df = pd.DataFrame({
        'PCA1': pca_result[:, 0],
        'PCA2': pca_result[:, 1],
        'label': labels
    })

    # Plot using Plotly Express
    fig = px.scatter(pca_df, x='PCA1', y='PCA2', color='label',
                    title='PCA of the Dataset',
                    labels={'color': 'labels'},
                    hover_data={'label': True})

    fig.update_layout(legend_title_text='Labels')
    fig.show()

    # Create a scree plot
    plt.figure(figsize=(10, 5))
    plt.plot(range(1, len(variance_explained) + 1), variance_explained, 'o-', linewidth=2, color='blue')
    plt.title('Scree Plot for PCA')
    plt.xlabel('Principal Component')
    plt.ylabel('Variance Explained')
    plt.xticks(range(1, len(variance_explained) + 1))
    plt.grid(True)
    plt.show()

    # Plotting the heatmap of loadings
    plt.figure(figsize=(12, 8))
    sns.heatmap(loadings_df, cmap='coolwarm' , center=0)
    plt.title('PCA Contributions Plot for Spectral Data')
    plt.xticks(rotation=45)
    plt.show()

    # Plotting the line plot of loadings
    plt.figure(figsize=(12, 6))
    for i in range(p):
        plt.plot(loadings[:, i], label=f'PCA{i+1}')

    plt.title('PCA Loadings Line Plot for Spectral Data')
    plt.xlabel('Wavelength index')
    plt.ylabel('Loading Value')
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.show()

    # Q/T Plot
    T2 = np.sum((pca_result ** 2) / variance_explained, axis=1)
    Q = np.sum((data_for_pca - X_reconstructed) ** 2, axis=1)

    alpha = 0.05
    F_critical = f.ppf(1 - alpha, p, n - p)
    T2_limit = (n - 1) * p / (n - p) * F_critical
    Q_limit = np.percentile(Q, 95)

    tq_df = pd.DataFrame({
        'T2': T2,
        'Q': Q,
        'label': labels
    })

    fig = px.scatter(tq_df, x='T2', y='Q', color='label',
                    title="Hotelling's T^2 vs Q Residuals Plot with Labels",
                    labels={'T2': "Hotelling's T^2", 'Q': 'Q Residuals'},
                    hover_data={'label': True})

    fig.add_vline(x=T2_limit, line_dash="dash", line_color="red", annotation_text=f"T^2 95% limit ({T2_limit:.2f})")
    fig.add_hline(y=Q_limit, line_dash="dash", line_color="blue", annotation_text=f"Q 95% limit ({Q_limit:.2f})")
    fig.show()

def plot_pca_scores_heatmap(pca_result, labels):
    scores_pca1 = pca_result[:, 0]
    
    df_scores = pd.DataFrame({
        "label": labels,
        "PCA1": scores_pca1
    })
    
    df_scores["replicate"] = df_scores.groupby("label").cumcount() + 1
    
    B_df = df_scores.pivot(
        index="replicate",
        columns="label",
        values="PCA1"
    )
    
    B = B_df.values
    
    plt.imshow(B, cmap="viridis", aspect="auto")
    
    plt.xticks(
        ticks=np.arange(B_df.shape[1]),
        labels=B_df.columns
    )
    
    plt.yticks(
        ticks=np.arange(B_df.shape[0]),
        labels=B_df.index
    )
    
    plt.xlabel("Class")
    plt.ylabel("Replicate")
    plt.colorbar(label="PCA1 score")
    
    plt.title("PCA1 scores by class and replicate")
    plt.show()
