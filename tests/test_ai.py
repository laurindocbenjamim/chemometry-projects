import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from src.main import app

client = TestClient(app)

def test_analyze_plot_unauthorized():
    """Verify that a 401 error is returned when session cookie is absent."""
    # Build a requests request bypassing middleware auto-inject by sending a direct route check
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.domains.ai.router import router as test_router
    
    # Isolate router to test security without middleware auto-injects
    isolated_app = FastAPI()
    isolated_app.include_router(test_router)
    isolated_client = TestClient(isolated_app)
    
    response = isolated_client.post("/ai/analyze-plot", json={
        "image_base64": "data:image/png;base64,mockbase64",
        "plot_type": "Scores Plot",
        "context": "Testing unauthorized"
    })
    assert response.status_code == 401
    assert "Session expired or invalid" in response.json()["detail"]

def test_analyze_plot_missing_image():
    """Verify that a 400 error is returned when base64 image data is empty."""
    # Test with active mock cookie
    response = client.post(
        "/ai/analyze-plot",
        json={
            "image_base64": "",
            "plot_type": "Scree Plot",
            "context": "Testing missing images"
        },
        cookies={"session_token": "active-test-session"}
    )
    assert response.status_code == 400
    assert "Missing required image data" in response.json()["detail"]

@patch("src.domains.ai.router.analyze_plot_with_groq")
def test_analyze_plot_success(mock_analyze):
    """Verify successful mock responses from Groq Llama VLM services."""
    mock_analyze.return_value = "### Scientific Diagnostics\n* Projections show standard separation."
    
    response = client.post(
        "/ai/analyze-plot",
        json={
            "image_base64": "data:image/png;base64,mockbase64",
            "plot_type": "Scores Plot",
            "context": "Analyzing sample separation."
        },
        cookies={"session_token": "active-test-session"}
    )
    
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert "Scientific Diagnostics" in res_data["analysis"]
    mock_analyze.assert_called_once_with(
        image_base64="data:image/png;base64,mockbase64",
        plot_type="Scores Plot",
        context="Analyzing sample separation."
    )

def test_ask_question_unauthorized():
    """Verify that a 401 error is returned for /ai/ask-question when session cookie is absent."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.domains.ai.router import router as test_router
    
    isolated_app = FastAPI()
    isolated_app.include_router(test_router)
    isolated_client = TestClient(isolated_app)
    
    response = isolated_client.post("/ai/ask-question", json={
        "plot_type": "Scores Plot",
        "question": "Why are there outliers?"
    })
    assert response.status_code == 401
    assert "Session expired or invalid" in response.json()["detail"]

@patch("src.domains.ai.router.answer_question_with_rag")
def test_ask_question_success(mock_answer):
    """Verify successful mock responses for /ai/ask-question endpoint."""
    mock_answer.return_value = "Outliers are present due to SNV offsets."
    
    response = client.post(
        "/ai/ask-question",
        json={
            "plot_type": "Scores Plot",
            "question": "Why are there outliers?"
        },
        cookies={"session_token": "active-test-session"}
    )
    
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert "Outliers are present" in res_data["answer"]
    mock_answer.assert_called_once_with(
        session_token="active-test-session",
        plot_type="Scores Plot",
        question="Why are there outliers?"
    )

def test_redis_memory_manager_fallback():
    """Verify that RedisMemoryManager handles storage/retrieval via fallback if URL is empty."""
    from src.domains.ai.memory import RedisMemoryManager
    
    # Instantiate custom manager with no Redis URL to trigger fallback
    manager = RedisMemoryManager(override_url="")
    
    session = "test-session-token"
    pt = "Scree Plot"
    analysis = "Mock Scree analysis showing variance."
    ctx = "Researching baseline values."
    
    # Save, register, and retrieve
    manager.save_plot_analysis(session, pt, analysis, ctx)
    manager.register_plot_in_session(session, pt)
    
    data = manager.get_plot_analysis(session, pt)
    assert data["plot_type"] == pt
    assert data["analysis"] == analysis
    assert data["context"] == ctx
    
    session_ctx = manager.get_session_context(session)
    assert "Scree Plot" in session_ctx
    assert "Mock Scree analysis" in session_ctx

