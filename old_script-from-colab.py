from google.colab import files
import glob
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from sklearn.decomposition import PCA
import plotly.express as px
import matplotlib.colors as mcolors
import seaborn as sns
from scipy.stats import f




def load_texas_instruments_data(
    pathname: str, excel_name: str = None, factory_reference: list = None
) -> pd.DataFrame:
    """
    Import data from Texas Instruments CSV files and return a pandas DataFrame.

    Args:
        pathname (str): Path to the directory containing the CSV files.
        csv_name (str, optional): Name of the output CSV file. Defaults to None.
        factory_reference (str): Use the factory reference

    Returns:
        pd.DataFrame: DataFrame containing the imported data.
    """
    csv_files = glob.glob(os.path.join(pathname, "*.csv"))
    data = []
    names = []

    for csv_file in csv_files:
        names.append(os.path.basename(csv_file).replace(".csv", ""))
        df_aux = pd.read_csv(csv_file, skiprows=21, encoding="cp1252") #21 for sg1, 28 for R13

        if factory_reference is not None:
            reference = np.array(factory_reference)
            intensity = df_aux["Sample Signal (unitless)"].to_numpy()
            absorbance = np.log10((reference / intensity))
            absorbance = list(absorbance)
        else:
            absorbance = df_aux["Absorbance (AU)"].to_list()
        data.append(absorbance)
    df = pd.DataFrame(data, columns=df_aux["Wavelength (nm)"].to_list())
    df.insert(0, "Name", names)

    if excel_name:
        csv_path = os.path.join(pathname, f"{excel_name}.xlsx")
        df.to_excel(csv_path, index=False)
    return df



    from google.colab import files
uploaded = files.upload()





df = load_texas_instruments_data(pathname='/content/', excel_name='output_excel')
labels=df['Name']
labels = [label[0] for label in labels]
df.groupby(labels)
data=df.iloc[:,1:228].to_numpy()
labels=np.array(labels)




def plot_data_classes(data,labels):
  unique_labels = np.unique(labels)
  colors = plt.cm.jet(np.linspace(0, 1, len(unique_labels)))  # Criar um mapa de cores

  # Mapear rótulos para cores
  label_color_map = {label: color for label, color in zip(unique_labels, colors)}

  # Lista para armazenar as linhas para a legenda
  legend_lines = []
  legend_labels = []

  for label in unique_labels:
      spectra = data[labels == label]
      color = label_color_map[label]

      for spectrum in spectra:
          line, = plt.plot(spectrum, color=color)

      # Adicionar apenas uma entrada na legenda para cada classe
      if label not in legend_labels:
          legend_lines.append(line)
          legend_labels.append(label)

  plt.title('Spectral Lines by Label')
  plt.xlabel('Wavelength Index')
  plt.ylabel('Intensity')
  plt.legend(legend_lines, legend_labels)
  plt.show()




  def plot_pca(pca, variance_explained, loadings, n, p, X_reconstructed):
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

  # Add customizations if you like
  fig.update_layout(legend_title_text='Labels')

  # Show the plot
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


  #Q/T
  # Calculating T^2 (Hotelling's T-square) and Q residuals for the PCA result
  T2 = np.sum((pca_result ** 2) / variance_explained, axis=1)  # Hotelling's T^2

  # Calculating Q residuals
  Q = np.sum((data_for_pca - X_reconstructed) ** 2, axis=1)  # Q residuals


  # Setting confidence level for the control limits
  alpha = 0.05  # for 95% confidence

  # Calculating control limit for T^2
  F_critical = f.ppf(1 - alpha, p, n - p)  # Critical value of F-distribution
  T2_limit = (n - 1) * p / (n - p) * F_critical

  # Estimating control limit for Q (using the 95th percentile as an approximation)
  Q_limit = np.percentile(Q, 95)

  # Creating a DataFrame for T^2 vs Q residuals with labels
  tq_df = pd.DataFrame({
      'T2': T2,
      'Q': Q,
      'label': labels
  })

  # Creating the plot with Plotly Express
  fig = px.scatter(tq_df, x='T2', y='Q', color='label',
                  title="Hotelling's T^2 vs Q Residuals Plot with Labels",
                  labels={'T2': "Hotelling's T^2", 'Q': 'Q Residuals'},
                  hover_data={'label': True})

  # Adding control limit lines
  fig.add_vline(x=T2_limit, line_dash="dash", line_color="red", annotation_text=f"T^2 95% limit ({T2_limit:.2f})")
  fig.add_hline(y=Q_limit, line_dash="dash", line_color="blue", annotation_text=f"Q 95% limit ({Q_limit:.2f})")

  # Show the plot
  fig.show()





  #Raw plot
for spectrum in data:
    line, = plt.plot(spectrum, color='black')
plt.show()

print("Shape of data:", data.shape)
print("Shape of labels:", labels.shape )




#Raw with labels
plot_data_classes(data,labels)

# Your normalized data from the previous step
data_for_pca = data

p=2# number of principal components

pca = PCA(n_components=p)  # You can change the number of components as needed

# Now you can apply PCA to the reshaped data
pca_result = pca.fit_transform(data_for_pca)

variance_explained = pca.explained_variance_ratio_

n = data_for_pca.shape[0]  # number of samples

loadings = pca.components_.T  # Transpose to align with original wavelengths
loadings_df = pd.DataFrame(loadings, columns=[f'PCA{i+1}' for i in range(pca.n_components)])

X_reconstructed = pca.inverse_transform(pca_result)

plot_pca(pca_result, variance_explained, loadings, n, p, X_reconstructed)







#SNV Function

def calculate_snv(x):
    x_mean = np.mean(x, keepdims=True, axis=1)
    x_std = np.std(x, keepdims=True, axis=1)
    x_snv = (x - x_mean) / x_std
    return x_snv

data=calculate_snv(data)
plot_data_classes(data,labels)

# Your normalized data from the previous step
data_for_pca = data

p=2# number of principal components

pca = PCA(n_components=p)  # You can change the number of components as needed

# Now you can apply PCA to the reshaped data
pca_result = pca.fit_transform(data_for_pca)

variance_explained = pca.explained_variance_ratio_

n = data_for_pca.shape[0]  # number of samples

loadings = pca.components_.T  # Transpose to align with original wavelengths
loadings_df = pd.DataFrame(loadings, columns=[f'PCA{i+1}' for i in range(pca.n_components)])

X_reconstructed = pca.inverse_transform(pca_result)

plot_pca(pca_result, variance_explained, loadings, n, p, X_reconstructed)





# Savitzky-Golay Filter

from scipy.signal import savgol_filter

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

    # window_length must be odd
    if window_length % 2 == 0:
        window_length += 1

    # window_length cannot be larger than the number of variables
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


data = savitzky_golay_filter(
    data,
    window_length=15,
    polyorder=2,
    deriv=0
)

plot_data_classes(data, labels)

# Your filtered data from the previous step
data_for_pca = data

p = 2  # number of principal components

pca = PCA(n_components=p)

# Apply PCA to the filtered data
pca_result = pca.fit_transform(data_for_pca)

variance_explained = pca.explained_variance_ratio_

n = data_for_pca.shape[0]  # number of samples

loadings = pca.components_.T
loadings_df = pd.DataFrame(
    loadings,
    columns=[f'PCA{i+1}' for i in range(pca.n_components_)]
)

X_reconstructed = pca.inverse_transform(pca_result)

plot_pca(
    pca_result,
    variance_explained,
    loadings,
    n,
    p,
    X_reconstructed
)







#Mean Center
def mean_centering(X):
    """
    Perform mean centering on the input dataset.

    Args:
    X (np.ndarray): Input dataset of shape (num_samples, num_variables, num_time_steps).

    Returns:
    X_centered (np.ndarray): Mean-centered dataset.
    """

    # Calculate the mean for each variable (column) in the input dataset
    variable_means = np.mean(X, axis=0)

    # Perform mean centering
    X_centered = X - variable_means

    return X_centered


data=mean_centering(data)


plot_data_classes(data,labels)

# Your normalized data from the previous step
data_for_pca = data

p=2# number of principal components

pca = PCA(n_components=p)  # You can change the number of components as needed

# Now you can apply PCA to the reshaped data
pca_result = pca.fit_transform(data_for_pca)

variance_explained = pca.explained_variance_ratio_

n = data_for_pca.shape[0]  # number of samples

loadings = pca.components_.T  # Transpose to align with original wavelengths
loadings_df = pd.DataFrame(loadings, columns=[f'PCA{i+1}' for i in range(pca.n_components)])

X_reconstructed = pca.inverse_transform(pca_result)

plot_pca(pca_result, variance_explained, loadings, n, p, X_reconstructed)

#ONLY LOOKS THE SAME BECAUSE SKLEARN VERSION ALREADY CENTERS THE DATA, BE CAREFUL DOING PCA OUTSIDE SKLEARNS SCOPE







df_scores = pd.DataFrame({
    "label": labels,
    "PCA1": scores_pca1
})

# Create replicate number within each class
df_scores["replicate"] = df_scores.groupby("label").cumcount() + 1

# Create matrix: rows = replicate, columns = class label
B_df = df_scores.pivot(
    index="replicate",
    columns="label",
    values="PCA1"
)

# Optional: force column order
B_df = B_df[["a", "b", "c", "d"]]

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



