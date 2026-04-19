"""Claude API client for AeroOps AI."""

import os

from dotenv import load_dotenv

from ai.context_builder import build_ai_context, format_context_for_prompt
from ai.prompts import (
    CHAT_PROMPT,
    DIAGNOSIS_PROMPT,
    RECOMMENDATION_PROMPT,
    SYSTEM_PROMPT,
)

NO_API_KEY_MSG = (
    "ANTHROPIC_API_KEY is not configured. Please set it in your .env file "
    "to enable Claude AI integration. Example:\n"
    "  ANTHROPIC_API_KEY=sk-ant-..."
)


class ClaudeClient:
    """Client for interacting with Claude API for AeroOps diagnostics."""

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        self.client = None

        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except Exception:
                self.client = None

    def _has_client(self) -> bool:
        return self.client is not None and self.api_key is not None

    def _send_message(self, user_content: str, max_tokens: int = 4096) -> str:
        """Send a message to Claude and return the response text."""
        if not self._has_client():
            return NO_API_KEY_MSG
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
        """Send pipeline context to Claude for incident diagnosis."""
        context_text = format_context_for_prompt(context)
        prompt = DIAGNOSIS_PROMPT.format(context=context_text)
        return self._send_message(prompt)

    def recommend(self, context: dict, question: str = None) -> str:
        """Get optimization recommendations from Claude."""
        context_text = format_context_for_prompt(context)
        extra = f"\nAdditional focus area: {question}" if question else ""
        prompt = RECOMMENDATION_PROMPT.format(context=context_text, question=extra)
        return self._send_message(prompt)

    def chat(self, messages: list, context: dict) -> str:
        """Interactive chat with grounding context.

        Args:
            messages: List of {"role": "user"|"assistant", "content": str} dicts.
            context: System context dict from build_ai_context().
        """
        if not self._has_client():
            return NO_API_KEY_MSG

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

        try:
            import anthropic
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
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
