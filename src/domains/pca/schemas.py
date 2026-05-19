from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional

class PreprocessingConfig(BaseModel):
    snv: bool = Field(True, description="Apply Standard Normal Variate (SNV)")
    sg_filter: bool = Field(True, description="Apply Savitzky-Golay filter")
    sg_window_length: int = Field(15, description="SG filter window length (must be odd)", ge=3)
    sg_polyorder: int = Field(2, description="SG polynomial order", ge=1)
    sg_deriv: int = Field(0, description="SG derivative order (0, 1 or 2)", ge=0, le=2)
    mean_center: bool = Field(True, description="Apply mean centering")

    @field_validator('sg_window_length')
    @classmethod
    def validate_window_length(cls, v: int) -> int:
        if v % 2 == 0:
            raise ValueError("Savitzky-Golay window length must be an odd integer.")
        return v

    @field_validator('sg_polyorder')
    @classmethod
    def validate_polyorder(cls, v: int, info) -> int:
        # Check window_length in raw input
        window_length = info.data.get('sg_window_length', 15)
        if v >= window_length:
            raise ValueError("Polynomial order must be strictly less than the window length.")
        return v

class PipelineRequest(BaseModel):
    algorithm: str = Field("PCA", description="Algorithm to run: 'PCA', 'PLS', or 'RAMAN'")
    format: str = Field("auto", description="File format selection: 'csv', 'sp', or 'auto'")
    preprocessing: PreprocessingConfig = Field(default_factory=PreprocessingConfig)
    n_components: int = Field(2, description="Number of components/latent variables", ge=1)
    raman_lambda: float = Field(1e5, description="Lambda smoothness parameter for ALS")
    raman_p: float = Field(0.01, description="p asymmetry parameter for ALS", ge=0.0, le=1.0)

    @field_validator('algorithm')
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        valid_algos = {"PCA", "PLS", "RAMAN"}
        v_upper = v.upper()
        if v_upper not in valid_algos:
            raise ValueError(f"Algorithm must be one of {valid_algos}")
        return v_upper

    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        valid_formats = {"csv", "sp", "auto"}
        v_lower = v.lower()
        if v_lower not in valid_formats:
            raise ValueError(f"Format must be one of {valid_formats}")
        return v_lower

class PipelineResponse(BaseModel):
    success: bool
    algorithm: str
    detected_format: str
    samples_count: int
    wavelengths_count: int
    plots: Dict[str, Any]
    original_plots: Optional[Dict[str, str]] = None
    error: Optional[str] = None
