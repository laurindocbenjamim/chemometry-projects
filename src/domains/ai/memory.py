import json
import urllib.request
import urllib.error
import logging
from typing import Optional, List
from src.config.config import settings

logger = logging.getLogger("upstash_memory")

class RedisMemoryManager:
    """
    Manages session diagnostics memory using Upstash Redis REST API with fallback.
    All public functions include docstring documentation.
    """
    def __init__(self, override_url: Optional[str] = None):
        """Initializes connection credentials and falls back gracefully if unavailable."""
        self.url = override_url if override_url is not None else settings.UPSTASH_REDIS_REST_URL
        self.token = settings.UPSTASH_REDIS_REST_TOKEN
        self._fallback_db = {}
        self.is_active = False

        if self.url and self.token:
            try:
                # Validate connectivity using standard PING
                res = self._execute_command(["PING"])
                if res == "PONG":
                    self.is_active = True
                    logger.info("Connected to Upstash Redis REST service.")
            except Exception as e:
                logger.warning(f"Upstash connection test failed: {e}. Falling back to local dictionary storage.")
        else:
            logger.info("Upstash REST URL or Token not configured. Using local in-memory storage.")

    def _execute_command(self, cmd: List) -> Optional[any]:
        """Sends a raw Redis command as a JSON array to the Upstash REST endpoint."""
        if not self.url or not self.token:
            raise ValueError("Upstash credentials not configured.")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        # Upstash REST endpoint executes commands passed in the request body as JSON arrays
        req = urllib.request.Request(
            self.url,
            data=json.dumps(cmd).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if "error" in res_data:
                raise ValueError(res_data["error"])
            return res_data.get("result")

    def save_plot_analysis(self, session_token: str, plot_type: str, analysis: str, context: str) -> None:
        """Stores plot diagnostics as a hash in Redis/fallback with a 24-hour expiration."""
        key = f"chemometry:session:{session_token}:plot:{plot_type}"
        cmd = ["HSET", key, "plot_type", plot_type, "analysis", analysis, "context", context]
        if self.is_active:
            try:
                self._execute_command(cmd)
                self._execute_command(["EXPIRE", key, "86400"])
            except Exception as e:
                logger.error(f"Upstash HSET failed: {e}. Storing in fallback cache.")
                self._fallback_db[key] = {"plot_type": plot_type, "analysis": analysis, "context": context}
        else:
            self._fallback_db[key] = {"plot_type": plot_type, "analysis": analysis, "context": context}

    def get_plot_analysis(self, session_token: str, plot_type: str) -> dict:
        """Retrieves plot details from Redis or fallback cache."""
        key = f"chemometry:session:{session_token}:plot:{plot_type}"
        if self.is_active:
            try:
                res = self._execute_command(["HGETALL", key])
                if res and isinstance(res, list):
                    # Upstash REST HGETALL returns flat array [field1, val1, field2, val2, ...]
                    return {res[i]: res[i+1] for i in range(0, len(res), 2)}
            except Exception as e:
                logger.error(f"Upstash HGETALL failed: {e}. Trying fallback.")
        return self._fallback_db.get(key, {})

    def register_plot_in_session(self, session_token: str, plot_type: str) -> None:
        """Registers the plot type in the active session's tracking set."""
        key = f"chemometry:session:{session_token}:plots"
        if self.is_active:
            try:
                self._execute_command(["SADD", key, plot_type])
                self._execute_command(["EXPIRE", key, "86400"])
            except Exception as e:
                logger.error(f"Upstash SADD failed: {e}.")
        
        # Keep tracked locally for backup robustness
        fallback_set_key = f"chemometry:session:{session_token}:plots_set"
        if fallback_set_key not in self._fallback_db:
            self._fallback_db[fallback_set_key] = set()
        self._fallback_db[fallback_set_key].add(plot_type)

    def get_session_context(self, session_token: str) -> str:
        """Assembles a text summary of all plots generated in this session for RAG context."""
        key = f"chemometry:session:{session_token}:plots"
        plot_types = set()
        
        if self.is_active:
            try:
                res = self._execute_command(["SMEMBERS", key])
                if res and isinstance(res, list):
                    plot_types.update(res)
            except Exception as e:
                logger.error(f"Upstash SMEMBERS failed: {e}.")

        # Retrieve locally tracked set as backup/union
        fallback_set_key = f"chemometry:session:{session_token}:plots_set"
        if fallback_set_key in self._fallback_db:
            plot_types.update(self._fallback_db[fallback_set_key])

        rag_texts = []
        for pt in sorted(plot_types):
            details = self.get_plot_analysis(session_token, pt)
            if details:
                rag_texts.append(
                    f"--- PLOT TYPE: {details.get('plot_type')} ---\n"
                    f"Researcher Context: {details.get('context')}\n"
                    f"AI Scientific Diagnostics: {details.get('analysis')}\n"
                )
        return "\n".join(rag_texts)

# Singleton instancer
redis_memory = RedisMemoryManager()
