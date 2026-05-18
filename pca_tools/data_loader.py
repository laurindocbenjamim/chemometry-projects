import glob
import os
import pandas as pd
import numpy as np

def load_texas_instruments_data(
    pathname: str,
    excel_name: str = None,
    factory_reference: list = None,
    skiprows: int = 21,
) -> pd.DataFrame:
    """
    Import data from Texas Instruments CSV files and return a pandas DataFrame.

    Args:
        pathname (str): Path to the directory containing the CSV files.
        excel_name (str, optional): Name of the output Excel file. Defaults to None.
        factory_reference (list, optional): Use the factory reference.
        skiprows (int): Number of rows to skip at the beginning of the CSV file. Defaults to 21.

    Returns:
        pd.DataFrame: DataFrame containing the imported data.
    """
    csv_files = glob.glob(os.path.join(pathname, "*.csv"))
    data = []
    names = []

    for csv_file in csv_files:
        names.append(os.path.basename(csv_file).replace(".csv", ""))
        df_aux = pd.read_csv(csv_file, skiprows=skiprows, encoding="cp1252")

        absorbance_column = next(
            (c for c in df_aux.columns if "Absorbance" in c), None
        )
        sample_signal_column = next(
            (c for c in df_aux.columns if "Sample Signal" in c), None
        )
        reference_signal_column = next(
            (c for c in df_aux.columns if "Reference Signal" in c), None
        )

        if factory_reference is not None:
            if sample_signal_column is None:
                raise KeyError(
                    "Could not find a sample signal column in the CSV file."
                )
            reference = np.array(factory_reference)
            intensity = df_aux[sample_signal_column].to_numpy()
            absorbance = np.log10(reference / intensity)
            absorbance = list(absorbance)
        else:
            if absorbance_column is None:
                raise KeyError(
                    "Could not find an absorbance column in the CSV file."
                )
            absorbance = df_aux[absorbance_column].to_list()
        data.append(absorbance)
    df = pd.DataFrame(data, columns=df_aux["Wavelength (nm)"].to_list())
    df.insert(0, "Name", names)

    if excel_name:
        csv_path = os.path.join(pathname, f"{excel_name}.xlsx")
        df.to_excel(csv_path, index=False)
    return df
