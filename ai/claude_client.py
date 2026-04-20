"""LLM client for AeroOps AI — supports Claude API and Ollama (local Llama)."""

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from ai.context_builder import build_ai_context, format_context_for_prompt
from ai.prompts import (
    CHAT_PROMPT,
    DIAGNOSIS_PROMPT,
    RECOMMENDATION_PROMPT,
    SYSTEM_PROMPT,
)

NO_LLM_MSG = (
    "No LLM backend available. Either:\n"
    "  • Start Ollama locally (`ollama serve`) with a model pulled, or\n"
    "  • Set ANTHROPIC_API_KEY in your .env file for Claude API."
)

# Claude Haiku pricing per 1M tokens (USD)
_PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
}
_DEFAULT_PRICING = {"input": 1.00, "output": 5.00}

_AI_METRICS_PATH = Path(__file__).resolve().parent.parent / "data" / "logs" / "ai_metrics.json"


def _log_ai_metric(entry: dict):
    """Append a metric entry to the AI metrics log file."""
    _AI_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    metrics = []
    if _AI_METRICS_PATH.exists():
        try:
            metrics = json.loads(_AI_METRICS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            metrics = []
    metrics.append(entry)
    _AI_METRICS_PATH.write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")


def load_ai_metrics() -> list[dict]:
    """Load all AI metrics from disk."""
    if not _AI_METRICS_PATH.exists():
        return []
    try:
        return json.loads(_AI_METRICS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _ollama_available(base_url: str = "http://localhost:11434") -> bool:
    """Check if Ollama is running and reachable."""
    try:
        req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def _ollama_chat(
    messages: list,
    system: str = "",
    model: str = "llama3",
    base_url: str = "http://localhost:11434",
) -> str:
    """Send a chat request to Ollama's /api/chat endpoint."""
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}] + messages,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("message", {}).get("content", "No response from model.")


class ClaudeClient:
    """LLM client that prefers Ollama (free, local) and falls back to Claude API."""

    def __init__(self):
        load_dotenv()
        self.backend = None  # "ollama" | "claude"
        self.client = None
        self.model = None

        # 1. Try Claude API first (fast, cloud-hosted)
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=api_key)
                self.backend = "claude"
                self.model = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
                return
            except Exception:
                pass

        # 2. Fall back to Ollama (free, local)
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
        if _ollama_available():
            self.backend = "ollama"
            self.model = ollama_model

    def _has_client(self) -> bool:
        return self.backend is not None

    def _get_backend_label(self) -> str:
        if self.backend == "ollama":
            return f"Ollama ({self.model})"
        elif self.backend == "claude":
            return f"Claude ({self.model})"
        return "None"

    def _send_message(self, user_content: str, max_tokens: int = 1024, prompt_type: str = "unknown") -> str:
        """Send a message to the active LLM backend."""
        if not self._has_client():
            return NO_LLM_MSG

        t0 = time.time()

        if self.backend == "ollama":
            try:
                result = _ollama_chat(
                    messages=[{"role": "user", "content": user_content}],
                    system=SYSTEM_PROMPT,
                    model=self.model,
                )
                latency = round(time.time() - t0, 3)
                _log_ai_metric({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "backend": self.backend,
                    "model": self.model,
                    "prompt_type": prompt_type,
                    "latency_sec": latency,
                    "input_tokens": None,
                    "output_tokens": None,
                    "cost_usd": 0.0,
                    "status": "success",
                })
                return result
            except urllib.error.URLError:
                _log_ai_metric({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "backend": self.backend, "model": self.model,
                    "prompt_type": prompt_type, "latency_sec": round(time.time() - t0, 3),
                    "status": "error", "error_type": "connection_error",
                })
                return "Error: Cannot connect to Ollama. Is it running? (`ollama serve`)"
            except Exception as e:
                _log_ai_metric({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "backend": self.backend, "model": self.model,
                    "prompt_type": prompt_type, "latency_sec": round(time.time() - t0, 3),
                    "status": "error", "error_type": type(e).__name__,
                })
                return f"Error communicating with Ollama: {e}"

        # Claude backend
        try:
            import anthropic
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            latency = round(time.time() - t0, 3)
            input_tokens = getattr(response.usage, "input_tokens", 0)
            output_tokens = getattr(response.usage, "output_tokens", 0)
            pricing = _PRICING.get(self.model, _DEFAULT_PRICING)
            cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

            _log_ai_metric({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "backend": self.backend,
                "model": self.model,
                "prompt_type": prompt_type,
                "latency_sec": latency,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost_usd": round(cost, 6),
                "status": "success",
            })
            return response.content[0].text
        except anthropic.APIConnectionError:
            _log_ai_metric({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "backend": self.backend, "model": self.model,
                "prompt_type": prompt_type, "latency_sec": round(time.time() - t0, 3),
                "status": "error", "error_type": "APIConnectionError",
            })
            return "Error: Unable to connect to Claude API. Check your network connection."
        except anthropic.RateLimitError:
            _log_ai_metric({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "backend": self.backend, "model": self.model,
                "prompt_type": prompt_type, "latency_sec": round(time.time() - t0, 3),
                "status": "error", "error_type": "RateLimitError",
            })
            return "Error: Claude API rate limit exceeded. Please try again in a moment."
        except anthropic.APIStatusError as e:
            _log_ai_metric({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "backend": self.backend, "model": self.model,
                "prompt_type": prompt_type, "latency_sec": round(time.time() - t0, 3),
                "status": "error", "error_type": f"APIStatusError_{e.status_code}",
            })
            return f"Error: Claude API returned status {e.status_code}: {e.message}"
        except Exception as e:
            _log_ai_metric({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "backend": self.backend, "model": self.model,
                "prompt_type": prompt_type, "latency_sec": round(time.time() - t0, 3),
                "status": "error", "error_type": type(e).__name__,
            })
            return f"Error communicating with Claude API: {e}"

    def diagnose(self, context: dict) -> str:
        """Send pipeline context to LLM for incident diagnosis."""
        context_text = format_context_for_prompt(context)
        prompt = DIAGNOSIS_PROMPT.format(context=context_text)
        return self._send_message(prompt, prompt_type="diagnose")

    def recommend(self, context: dict, question: str = None) -> str:
        """Get optimization recommendations from LLM."""
        context_text = format_context_for_prompt(context)
        extra = f"\nAdditional focus area: {question}" if question else ""
        prompt = RECOMMENDATION_PROMPT.format(context=context_text, question=extra)
        return self._send_message(prompt, prompt_type="recommend")

    def chat(self, messages: list, context: dict) -> str:
        """Interactive chat with grounding context."""
        if not self._has_client():
            return NO_LLM_MSG

        context_text = format_context_for_prompt(context)

        # Build the conversation with context injected into the first user message
        api_messages = []
        for i, msg in enumerate(messages):
            if i == 0 and msg["role"] == "user":
                grounded = CHAT_PROMPT.format(
                    context=context_text, question=msg["content"]
                )
                api_messages.append({"role": "user", "content": grounded})
            else:
                api_messages.append(msg)

        t0 = time.time()

        if self.backend == "ollama":
            try:
                result = _ollama_chat(
                    messages=api_messages,
                    system=SYSTEM_PROMPT,
                    model=self.model,
                )
                _log_ai_metric({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "backend": self.backend, "model": self.model,
                    "prompt_type": "chat", "latency_sec": round(time.time() - t0, 3),
                    "input_tokens": None, "output_tokens": None, "cost_usd": 0.0,
                    "status": "success",
                })
                return result
            except Exception as e:
                _log_ai_metric({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "backend": self.backend, "model": self.model,
                    "prompt_type": "chat", "latency_sec": round(time.time() - t0, 3),
                    "status": "error", "error_type": type(e).__name__,
                })
                return f"Error communicating with Ollama: {e}"

        # Claude backend
        try:
            import anthropic
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=api_messages,
            )
            latency = round(time.time() - t0, 3)
            input_tokens = getattr(response.usage, "input_tokens", 0)
            output_tokens = getattr(response.usage, "output_tokens", 0)
            pricing = _PRICING.get(self.model, _DEFAULT_PRICING)
            cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

            _log_ai_metric({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "backend": self.backend, "model": self.model,
                "prompt_type": "chat", "latency_sec": latency,
                "input_tokens": input_tokens, "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost_usd": round(cost, 6), "status": "success",
            })
            return response.content[0].text
        except anthropic.APIConnectionError:
            _log_ai_metric({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "backend": self.backend, "model": self.model,
                "prompt_type": "chat", "latency_sec": round(time.time() - t0, 3),
                "status": "error", "error_type": "APIConnectionError",
            })
            return "Error: Unable to connect to Claude API. Check your network connection."
        except anthropic.RateLimitError:
            _log_ai_metric({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "backend": self.backend, "model": self.model,
                "prompt_type": "chat", "latency_sec": round(time.time() - t0, 3),
                "status": "error", "error_type": "RateLimitError",
            })
            return "Error: Claude API rate limit exceeded. Please try again in a moment."
        except anthropic.APIStatusError as e:
            _log_ai_metric({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "backend": self.backend, "model": self.model,
                "prompt_type": "chat", "latency_sec": round(time.time() - t0, 3),
                "status": "error", "error_type": f"APIStatusError_{e.status_code}",
            })
            return f"Error: Claude API returned status {e.status_code}: {e.message}"
        except Exception as e:
            _log_ai_metric({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "backend": self.backend, "model": self.model,
                "prompt_type": "chat", "latency_sec": round(time.time() - t0, 3),
                "status": "error", "error_type": type(e).__name__,
            })
            return f"Error communicating with Claude API: {e}"
