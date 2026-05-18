import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from src.main import app

client = TestClient(app)

def test_analyze_plot_missing_image():
    """Verify that a 400 error is returned when base64 image data is empty."""
    response = client.post("/ai/analyze-plot", json={
        "image_base64": "",
        "plot_type": "Scree Plot",
        "context": "Testing missing images"
    })
    assert response.status_code == 400
    assert "Missing required image data" in response.json()["detail"]

@patch("src.domains.ai.router.analyze_plot_with_groq")
def test_analyze_plot_success(mock_analyze):
    """Verify successful mock responses from Groq Llama VLM services."""
    mock_analyze.return_value = "### Scientific Diagnostics\n* Projections show standard separation."
    
    response = client.post("/ai/analyze-plot", json={
        "image_base64": "data:image/png;base64,mockbase64",
        "plot_type": "Scores Plot",
        "context": "Analyzing sample separation."
    })
    
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert "Scientific Diagnostics" in res_data["analysis"]
    mock_analyze.assert_called_once_with(
        image_base64="data:image/png;base64,mockbase64",
        plot_type="Scores Plot",
        context="Analyzing sample separation."
    )
