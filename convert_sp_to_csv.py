import pandas as pd
from specio import specread

color_data_path = "/home/feti/Documents/PythonProjects/chemometry-projects/test-project/Spectrometria/COLORS-20260519T140209Z-3-001"
concentration_data_path = "/home/feti/Documents/PythonProjects/chemometry-projects/test-project/Spectrometria/Concentration-20260519T140215Z-3-001"
# Load the file
spectra = specread("your_file.sp")

# Create a DataFrame
df = pd.DataFrame({
    'Wavelength': spectra.wavelength,
    'Amplitude': spectra.amplitudes
})

# Export to CSV
df.to_csv("your_file.csv", index=False)
