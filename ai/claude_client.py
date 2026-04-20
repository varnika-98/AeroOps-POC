"""LLM client for AeroOps AI — supports Claude API and Ollama (local Llama)."""

import json
import os
import urllib.error
import urllib.request

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

    def _send_message(self, user_content: str, max_tokens: int = 1024) -> str:
        """Send a message to the active LLM backend."""
        if not self._has_client():
            return NO_LLM_MSG

        if self.backend == "ollama":
            try:
                return _ollama_chat(
                    messages=[{"role": "user", "content": user_content}],
                    system=SYSTEM_PROMPT,
                    model=self.model,
                )
            except urllib.error.URLError:
                return "Error: Cannot connect to Ollama. Is it running? (`ollama serve`)"
            except Exception as e:
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
            return response.content[0].text
        except anthropic.APIConnectionError:
            return "Error: Unable to connect to Claude API. Check your network connection."
        except anthropic.RateLimitError:
            return "Error: Claude API rate limit exceeded. Please try again in a moment."
        except anthropic.APIStatusError as e:
            return f"Error: Claude API returned status {e.status_code}: {e.message}"
        except Exception as e:
            return f"Error communicating with Claude API: {e}"

    def diagnose(self, context: dict) -> str:
        """Send pipeline context to LLM for incident diagnosis."""
        context_text = format_context_for_prompt(context)
        prompt = DIAGNOSIS_PROMPT.format(context=context_text)
        return self._send_message(prompt)

    def recommend(self, context: dict, question: str = None) -> str:
        """Get optimization recommendations from LLM."""
        context_text = format_context_for_prompt(context)
        extra = f"\nAdditional focus area: {question}" if question else ""
        prompt = RECOMMENDATION_PROMPT.format(context=context_text, question=extra)
        return self._send_message(prompt)

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

        if self.backend == "ollama":
            try:
                return _ollama_chat(
                    messages=api_messages,
                    system=SYSTEM_PROMPT,
                    model=self.model,
                )
            except Exception as e:
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
            return response.content[0].text
        except anthropic.APIConnectionError:
            return "Error: Unable to connect to Claude API. Check your network connection."
        except anthropic.RateLimitError:
            return "Error: Claude API rate limit exceeded. Please try again in a moment."
        except anthropic.APIStatusError as e:
            return f"Error: Claude API returned status {e.status_code}: {e.message}"
        except Exception as e:
            return f"Error communicating with Claude API: {e}"
