# claude_client.py

> File: `ai/claude_client.py`

## Overview

LLM abstraction layer that provides a unified interface to two backends — Anthropic Claude API (cloud) and Ollama (local). Handles backend auto-detection, message routing, error handling, cost calculation, and metrics logging for every AI call in the system.

## Purpose

- **Backend abstraction** — Callers use `diagnose()`, `recommend()`, `chat()` without knowing which LLM is active
- **Graceful degradation** — App functions without any LLM (shows warning message)
- **Cost tracking** — Calculates per-call cost from token usage + pricing table
- **Observability** — Every call (success or failure) logs to `ai_metrics.json`
- **Error isolation** — API failures return user-friendly messages, never crash the app

## Anthropic SDK Usage

### Library: `anthropic` (Python SDK)

```python
import anthropic

# Initialization
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Message creation (core API call)
response = client.messages.create(
    model="claude-haiku-4-5-20251001",  # Model identifier
    max_tokens=1024,                     # Response length limit
    system=SYSTEM_PROMPT,                # System-level instructions
    messages=[                           # Conversation history
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "..."}
    ]
)

# Response extraction
text = response.content[0].text          # Generated text
input_tokens = response.usage.input_tokens   # Tokens consumed (prompt)
output_tokens = response.usage.output_tokens # Tokens generated (response)
```

### SDK Exception Hierarchy

| Exception | Trigger | Handling |
|-----------|---------|----------|
| `anthropic.APIConnectionError` | Network failure, DNS issues | "Check your network connection" |
| `anthropic.RateLimitError` | Too many requests (429) | "Try again in a moment" |
| `anthropic.APIStatusError` | 4xx/5xx responses | Show status code + message |
| Generic `Exception` | Unexpected errors | Log type name, show generic message |

### Why This SDK Pattern

1. **Synchronous calls** — Streamlit is synchronous; no need for async client
2. **System prompt separation** — SDK accepts `system` as a separate parameter (not a message role), ensuring it's always first and never confused with user content
3. **Token counting built-in** — `response.usage` provides exact token counts for cost calculation without external tokenizer
4. **Structured exceptions** — Each error type maps to a specific user-facing message

## Backend Selection Logic

```python
def __init__(self):
    # Priority 1: Claude API (if ANTHROPIC_API_KEY set)
    if os.getenv("ANTHROPIC_API_KEY"):
        self.client = anthropic.Anthropic(api_key=key)
        self.backend = "claude"
        self.model = "claude-haiku-4-5-20251001"
        return

    # Priority 2: Ollama (if server responding on localhost:11434)
    if _ollama_available():
        self.backend = "ollama"
        self.model = "llama3"
        return

    # Priority 3: No backend (graceful degradation)
    self.backend = None
```

## Key Methods

### `diagnose(context: dict) → str`
- Formats context via `format_context_for_prompt()`
- Injects into `DIAGNOSIS_PROMPT` template
- Sends as single user message with system prompt
- **prompt_type:** "diagnose"

### `recommend(context: dict, question: str = None) → str`
- Same context formatting
- Supports optional focus area question
- **prompt_type:** "recommend"

### `chat(messages: list, context: dict) → str`
- Multi-turn conversation support
- Injects context into FIRST user message only (not repeated)
- Passes full message history for continuity
- **prompt_type:** "chat"

### `_send_message(user_content: str, max_tokens, prompt_type) → str`
- Core routing method for single-turn calls (diagnose, recommend)
- Routes to active backend
- Times the call, logs metrics, calculates cost

## Cost Calculation

```python
_PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},   # $/1M tokens
    "claude-sonnet-4-20250514":  {"input": 3.00, "output": 15.00},
}

cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
```

**Ollama cost:** Always $0.00 (local inference)

## Metrics Logging

Every call appends to `data/logs/ai_metrics.json`:
```json
{
    "timestamp": "2026-04-20T16:30:00+00:00",
    "backend": "claude",
    "model": "claude-haiku-4-5-20251001",
    "prompt_type": "chat",
    "latency_sec": 2.847,
    "input_tokens": 1203,
    "output_tokens": 456,
    "total_tokens": 1659,
    "cost_usd": 0.002786,
    "status": "success"
}
```

Error entries additionally include `error_type` (e.g., "RateLimitError", "APIConnectionError").

## Ollama Integration

Uses raw HTTP (no SDK) via `urllib.request`:

```python
POST http://localhost:11434/api/chat
{
    "model": "llama3",
    "messages": [{"role": "system", ...}, {"role": "user", ...}],
    "stream": false  # Wait for complete response
}
```

**Why no Ollama SDK?** Keeps dependencies minimal. The Ollama API is a single POST endpoint — a 10-line function covers it.

## Interview Q&A

1. **Q: Why prioritize Claude over Ollama?**
   A: Claude API is faster (~2-4s vs 10-30s for Ollama on CPU), produces higher quality responses, and provides token counts for cost tracking. Ollama is the fallback for offline development or cost-sensitive usage. The priority can be swapped via environment variables.

2. **Q: How does the chat method maintain conversation context?**
   A: Full message history is passed to the API on every call. Claude's Messages API is stateless — it doesn't remember previous calls. The app stores history in `st.session_state["ai_messages"]` and sends the entire array each time. Context is injected only into the first user message to avoid token bloat.

3. **Q: Why log metrics to JSON instead of the pipeline's parquet?**
   A: AI metrics are app-level operational data, not IoT pipeline data. Mixing them into the Gold layer would corrupt the medallion architecture and fail pipeline quality rules. JSON is simple, append-only, and sufficient for the monitoring scale (~20-50 entries per session).

4. **Q: How would you add streaming responses?**
   A: Replace `messages.create()` with `messages.stream()` which returns an iterator. Yield chunks to the Streamlit UI via `st.write_stream()`. Log total tokens from the final `message_stop` event. The Ollama path already supports `"stream": true` in its API.

5. **Q: What happens if both backends are unavailable?**
   A: `self.backend = None`. All methods check `_has_client()` first and return `NO_LLM_MSG` — a user-friendly message explaining how to enable either backend. The rest of the dashboard functions normally; only AI Ops Center features are degraded.

6. **Q: Why use `getattr(response.usage, "input_tokens", 0)` instead of direct access?**
   A: Defensive coding — if the API response format changes or the `usage` object is missing a field, we get 0 instead of an AttributeError crash. Critical for production resilience.
