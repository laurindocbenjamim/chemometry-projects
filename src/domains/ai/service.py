import json
import logging
import urllib.request
import urllib.error
from src.config.config import settings

logger = logging.getLogger("ai_service")

def analyze_plot_with_groq(image_base64: str, plot_type: str, context: str) -> str:
    """
    Sends the plot image and research context to the configured VLM API (Groq or Ollama) for automated scientific review.
    """
    # 1. Clean up base64 prefix if present
    if "," in image_base64:
        image_base64 = image_base64.split(",")[1]
        
    provider = settings.LLMPROVIDER.lower() if settings.LLMPROVIDER else "groq"

    # Construct the scientific analysis prompt emphasizing context-driven diagnosis
    prompt_text = (
        f"You are a distinguished Senior Chemometrician and Data Scientist performing a rigorous peer-review level analysis of a {plot_type}.\n\n"
        f"CRITICAL RESEARCH CONTEXT:\n"
        f"{context if context else 'No study context provided. Perform a blind baseline chemometric analysis.'}\n\n"
        f"YOUR OBJECTIVE:\n"
        f"Diagnose this plot with extreme scientific precision. Do not just describe what you see visually (e.g., 'red dots on the right')—you must explain the *mathematical and chemical significance* of the visual structures (e.g., 'Samples in the upper right quadrant exhibit high Hotelling's T² indicating high leverage, driven by specific spectral features').\n\n"
        f"Please structure your diagnosis as follows:\n\n"
        f"**1. Methodological Purpose:**\n"
        f"Briefly explain the underlying chemometric theory of this specific plot type (e.g., what do Scores, Loadings, Scree, or Residuals mathematically represent in PCA/PLS/RAMAN models).\n\n"
        f"**2. Diagnostic Findings & Interpretation:**\n"
        f"- Analyze the variance, distributions, clustering patterns, or baseline shifts.\n"
        f"- Explicitly tie the visual groupings or variance capture (e.g., PC1 vs PC2) to the provided research context.\n"
        f"- Identify potential anomalies, outliers, over-fitting risks, or spectral artifacts.\n\n"
        f"**3. Strategic Recommendations:**\n"
        f"- What preprocessing step (SNV, SG Filter) or algorithmic shift should the researcher test next based on this visual data?\n\n"
        f"Output using crisp, professional markdown. Use bullet points for readability. Avoid generic fluff. Be highly analytical and strictly scientific."
    )

    if provider == "ollama":
        model = settings.LLMMODEL if settings.LLMMODEL else "llava"
        if not model:
            model = "llava"
        # Ollama local HTTP chat completion endpoint
        url = "http://localhost:11434/api/chat"
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt_text,
                    "images": [image_base64]
                }
            ],
            "stream": False
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.error(f"Ollama model '{model}' not found. Install a vision model: `ollama pull llava`")
                return f"Ollama Error: Model '{model}' not found. Run `ollama pull llava` to install a vision model, or set LLMPROVIDER=groq in .env."
            logger.error(f"Ollama HTTP Error: {str(e)}")
            return f"Ollama VLM Error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error calling Ollama VLM: {str(e)}")
            return f"Ollama VLM Connection Error: {str(e)}. Please verify Ollama is running locally (`ollama run {model}`)."

    else:
        # Fallback to remote Groq VLM Cloud
        api_key = settings.GROQ_API_KEY
        if not api_key:
            logger.error("GROQ_API_KEY is not configured in settings/environment.")
            return "Error: Groq API Key is missing. Please configure it in your .env file."

        model = settings.LLMMODEL if settings.LLMMODEL else "llama-3.2-11b-vision-preview"
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
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
            logger.error(f"Groq API HTTP Error: {err_msg}")
            try:
                err_json = json.loads(err_msg)
                return f"Groq VLM Error: {err_json['error']['message']}"
            except Exception:
                return f"Groq VLM Connection Error: {e.reason}"
        except Exception as e:
            logger.error(f"Unexpected error calling Groq VLM: {str(e)}")
            return f"Unexpected Error: {str(e)}"
