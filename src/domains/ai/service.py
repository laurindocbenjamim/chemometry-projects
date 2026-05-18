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

    # Construct the scientific analysis prompt
    prompt_text = (
        f"You are an expert chemometrician and data scientist analyzing a Spectroscopy/Chemometrics chart.\n"
        f"Plot Type: {plot_type}\n"
        f"Context of the Study (provided by researcher):\n"
        f"{context if context else 'No context provided.'}\n\n"
        f"Provide a concise, professional, and visually clear summary explaining:\n"
        f"1. What this specific plot represents in the chemometric workflow.\n"
        f"2. The key insights, patterns, groupings, or anomalies observable in this plot.\n"
        f"3. Recommendations or actions for subsequent processing.\n\n"
        f"Format your response using bold markdown headers and neat bullet points. Keep it highly factual, clear, and actionable. Limit to 3 short paragraphs."
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
