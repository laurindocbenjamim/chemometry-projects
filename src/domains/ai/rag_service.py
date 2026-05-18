import json
import logging
import urllib.request
import urllib.error
from src.config.config import settings
from src.domains.ai.memory import redis_memory

logger = logging.getLogger("rag_service")

def call_llm_text(prompt_text: str) -> str:
    """
    Sends a text completion prompt to the configured LLM API (Groq or Ollama).
    """
    provider = settings.LLMPROVIDER.lower() if settings.LLMPROVIDER else "groq"

    if provider == "ollama":
        model = settings.LLMMODEL if settings.LLMMODEL else "llama3"
        url = "http://localhost:11434/api/chat"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt_text}],
            "stream": False
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama text VLM error: {e}")
            return f"Ollama Connection Error: {str(e)}"

    else:
        # Groq endpoint fallback
        api_key = settings.GROQ_API_KEY
        if not api_key:
            return "Error: Groq API Key is missing. Please configure it in your .env file."

        model = settings.LLMMODEL if settings.LLMMODEL else "meta-llama/llama-4-scout-17b-16e-instruct"
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": 0.2,
            "max_tokens": 800
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            logger.error(f"Groq API Text Error: {err_msg}")
            return f"Groq LLM Error: {err_msg}"
        except Exception as e:
            logger.error(f"Groq text call connection error: {e}")
            return f"Groq Connection Error: {str(e)}"

def answer_question_with_rag(session_token: str, plot_type: str, question: str) -> str:
    """
    Performs RAG by fetching stored diagnostic facts from Upstash Redis,
    building a comprehensive context, and answering the user's scientific query.
    """
    # 1. Fetch exact targeted plot memory
    target_plot = redis_memory.get_plot_analysis(session_token, plot_type)
    
    # 2. Fetch cross-plot entire session diagnostic memory
    session_context = redis_memory.get_session_context(session_token)

    # 3. Construct contextual researcher prompt with strict bounds and visual clean guidelines
    prompt = (
        f"You are an expert chemometrician, data scientist, and spectroscopy researcher.\n"
        f"A user is asking a scientific question about a chart: {plot_type}.\n\n"
        f"CRITICAL SAFETY RULE: You must ONLY answer questions that are related strictly to the specific "
        f"spectroscopic plot/component ({plot_type}) being discussed. If the user's question is off-topic, "
        f"unrelated, or refers to another domain entirely, you must politely refuse to answer, explaining that "
        f"you are bounded by security guidelines to only discuss the active visual features, projections, "
        f"and diagnostics of the '{plot_type}' chart.\n\n"
        f"FORMATTING RULE: Do NOT under any circumstances output decorative separator lines, horizontal bars, "
        f"or repeating symbol sequences (such as ===, ---, ____, or »»»»). Keep your response clean, organic "
        f"markdown headings and bullet points.\n\n"
    )

    if target_plot:
        prompt += (
            f"TARGET PLOT ANALYSIS DETAILS:\n"
            f"Study Context: {target_plot.get('context', 'No context provided.')}\n"
            f"Original AI Plot Diagnosis:\n{target_plot.get('analysis')}\n\n"
        )
    else:
        prompt += "No original diagnostics found for this specific plot in memory.\n\n"

    if session_context:
        prompt += (
            f"ADDITIONAL SAMPLES/STAGES DIAGNOSTICS IN CURRENT STUDY SESSION:\n"
            f"Use the following multi-stage/preprocessed plot diagnostics for cross-reference or general insights:\n"
            f"{session_context}\n\n"
        )

    prompt += (
        f"RESEARCHER'S QUESTION:\n"
        f"Question: {question}\n\n"
        f"Provide a scientifically rigorous, direct, and factual response. "
        f"Take the researcher's context and experimental variables deeply into account. "
        f"Use bold markdown headers and neat bullet points. Limit to 3 short paragraphs."
    )

    return call_llm_text(prompt)
