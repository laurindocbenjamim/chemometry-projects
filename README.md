# SpectraLab — Spectroscopy & Chemometrics Dashboard

SpectraLab is a high-performance, modular monolithic web application built for chemometrics processing and spectroscopy analysis. It supports multiple file format uploads (.csv and .sp), performs real-time preprocessing, and executes unsupervised/supervised algorithms (PCA, PLS-DA, RAMAN) returning interactive visualizations for analytical chemistry.

> [!NOTE]
> Designed as a **Modular Monolith (Bounded Contexts)** to keep logic highly segregated, easily maintainable, and completely ready for future microservice extractions.

---

## 🏛️ Project Directory Structure

```text
test-project/
├── pca_tools/                  # Core Chemometrics package
│   ├── __init__.py             # Exposes math routines & SP readers
│   ├── data_loader.py          # TI CSV filesystem loader
│   ├── sp_reader.py            # PerkinElmer binary parser (sp & bytes)
│   ├── preprocessing.py        # SNV, Savitzky-Golay, ALS baseline correction
│   └── visualization.py        # Legacy Matplotlib visual orchestrators
├── public/                     # Frontend SPA Assets (Static files)
│   ├── index.html              # Modern glassmorphism layout dashboard
│   ├── styles.css              # Custom HSL responsive stylesheet
│   └── app.js                  # Axios controllers & ApexCharts charts
├── src/                        # FastAPI Monolithic Web App
│   ├── config/
│   │   └── config.py           # Pydantic Settings
│   ├── shared/
│   │   └── sentry.py           # Sentry integrations
│   ├── domains/
│   │   └── pca/                # Chemometrics / PCA bounded context
│   │       ├── router.py       # API routes, file validations, sanitizations
│   │       ├── service.py      # Core parser orchestrator & math executors
│   │       └── schemas.py      # Pydantic schema parameters constraints
│   └── main.py                 # FastAPI Application Gateway & Static Server
├── tests/                      # Testing contextual boundary
│   └── test_pca.py             # Math & pipeline automated tests (TDD)
├── requirements.txt            # Package dependencies
├── .gitignore                  # Excluded folders & environment files
└── pca_analysis.py             # Legacy local execution script
```

---

## ✨ Features and Tasks

### 📊 Supported Chemometrics Algorithms
- **PCA (Principal Component Analysis):** Auto-transforms multi-dimensional spectra into a 2D PCA Scores plot. Computes Scree Plots (variance ratios), Loadings curves, and Hotelling's $T^2$ vs Q residuals.
- **PLS-DA (Partial Least Squares Discriminant Analysis):** A supervised regression and classification algorithm designed to maximize class separations in low-dimensional score projections. Requires at least 2 distinct classes.
- **RAMAN Baseline Correction:** Applies standard **Asymmetric Least Squares (AsLS)** to subtract baseline fluorescence, isolating pure Raman vibrational peaks.

### ⚙️ Preprocessing Pipelines
- **SNV (Standard Normal Variate):** Centers and standardizes each spectrum ($mean=0, std=1$) to correct for light scattering distortions.
- **Savitzky-Golay Filtering:** Fits local polynomial approximations inside moving windows. Computes smooth approximations, 1st derivatives, or 2nd derivatives.
- **Mean Centering:** Centers variables across the sample batch.

### 🛡️ Validation & Sanitization Protocols
- **File Validation Layer:** Restricts extensions to `.csv` and `.sp` (PerkinElmer binary file header signature verification). Enforces file size limits (< 5MB).
- **Sanitization Layer:** Escapes HTML special entities to block cross-site scripting (XSS), and strips directory traversal indicators to protect directory trees.
- **Wavelengths Check:** Asserts that all loaded files share identical wavelength resolution and grids before performing array processing.
- **Sentry Integration:** Tracks client-side UI anomalies and uncaught backend pipeline errors out-of-the-box.

---

## 🚀 Installation & Running

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Setup Dependencies
Install package requirements in your environment:
```bash
pip install -r requirements.txt
```

### 3. Run the Dashboard
Start the monolithic FastAPI application:
```bash
python3 src/main.py
```
Or run directly via Uvicorn CLI:
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
Navigate to **`http://localhost:8000`** inside your web browser.

---

## 🧪 Running Automated Tests

To maintain correct-by-construction code, the project enforces automated testing before production code changes (TDD approach).

Run the math and API pipeline tests using Pytest:
```bash
pytest tests/
```
