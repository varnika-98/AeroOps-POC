# AI Performance Monitor

> File: `app/pages/6_AI_Performance_Monitor.py`

## Overview

The AI Performance Monitor tracks LLM usage analytics — latency, token consumption, cost, and error rates across all AI interactions. It provides operational visibility into the AI layer, enabling cost management and performance optimization.

**Supporting files:** `ai/claude_client.py` (`load_ai_metrics`, `_log_ai_metric`), `utils/kpi_calculator.py` (`get_ai_kpis`)

## Metrics

### KPI Cards

| Metric | Calculation | Thresholds | Data Source |
|--------|-------------|------------|-------------|
| **Total Requests** | Count of all entries in ai_metrics.json | Neutral | `data/logs/ai_metrics.json` |
| **Avg Latency** | Mean of `latency_sec` (success only) | 🟢 <5s · 🟡 <10s · 🔴 ≥10s | `data/logs/ai_metrics.json` |
| **Total Tokens** | Sum of `input_tokens + output_tokens` | Neutral | `data/logs/ai_metrics.json` |
| **Total Cost** | Sum of `cost_usd` | Neutral (USD) | `data/logs/ai_metrics.json` |
| **Error Rate** | `(error_count / total_count) × 100` | 🟢 <5% · 🟡 <20% · 🔴 ≥20% | `data/logs/ai_metrics.json` |

**Info Caption:** Model name, Backend type, Avg tokens/request

### Charts

| Chart | Type | Key Details |
|-------|------|-------------|
| **Response Latency Trend** | Line + colored markers | Green (<3s), Yellow (3-6s), Red (>6s) markers on steel blue line |
| **Token Usage by Prompt Type** | Grouped Bar | Input tokens (navy #0D3B66) vs Output tokens (teal #1A8FA8) per type |
| **Cost by Prompt Type** | Donut | Teal gradient slices, total cost in center annotation |
| **Requests by Prompt Type** | Bar | Count per type (diagnose, recommend, chat) |

### Prompt Types
- **diagnose** — System diagnosis generation
- **recommend** — Optimization recommendations
- **chat** — Interactive Q&A

### Pricing Model

| Model | Input ($/1M tokens) | Output ($/1M tokens) |
|-------|---------------------|----------------------|
| claude-haiku-4-5 | $0.80 | $4.00 |
| claude-sonnet-4 | $3.00 | $15.00 |
| Ollama (local) | $0.00 | $0.00 |
| Default fallback | $1.00 | $5.00 |

### Call Log Table
Columns: timestamp, prompt_type, status, latency_sec, input_tokens, output_tokens, total_tokens, cost_usd, model

### Per-Call Metric Structure
```json
{
  "timestamp": "ISO 8601",
  "backend": "claude|ollama",
  "model": "model-name",
  "prompt_type": "diagnose|recommend|chat",
  "latency_sec": 3.45,
  "input_tokens": 832,
  "output_tokens": 479,
  "total_tokens": 1311,
  "cost_usd": 0.002582,
  "status": "success|error"
}
```

## Purpose & Inference

| Metric | Purpose | What to Infer |
|--------|---------|---------------|
| Avg Latency | Response time monitoring | >10s indicates model overload or network issues; Ollama is typically slower than Claude API |
| Token Usage (input vs output) | Cost driver identification | High input tokens = large context; high output tokens = verbose responses. Optimize by trimming context |
| Cost by Type | Budget allocation | If "chat" dominates cost, consider limiting chat history length or switching to cheaper model |
| Error Rate | Reliability tracking | >5% needs investigation — API rate limits, network timeouts, or malformed prompts |
| Latency Trend | Performance degradation detection | Upward trend over time suggests increasing context size or API throttling |
| Requests by Type | Usage pattern analysis | Shows how users interact — mostly chat vs mostly diagnosis reveals UX preferences |

## Data Dependencies

| Data File | Layer | Read By | Content |
|-----------|-------|---------|---------|
| `data/logs/ai_metrics.json` | Logs | `load_ai_metrics()` → raw list, `get_ai_kpis()` → aggregated | Append-only JSON array of per-call metrics |

Each entry contains: timestamp, backend, model, prompt_type, latency_sec, input_tokens, output_tokens, total_tokens, cost_usd, status, error_type (if error).

**Write operations:** None (read-only page; writes happen in AI Ops Center via `claude_client._log_ai_metric()`)

## Interview Pitch

*"The AI Performance Monitor is our LLMOps observability layer. Every AI call is instrumented with timing, token counts, and cost. The grouped bar chart showing input vs output tokens per prompt type reveals that diagnose calls have high output (detailed analysis) while chat has more balanced I/O. The cost donut shows spend distribution. At $0.005 per diagnosis with Haiku, it's extremely cost-effective. This page demonstrates production-readiness — you can't deploy AI features without cost and performance monitoring."*

## Interview Questions

1. **Q: Why track input and output tokens separately?**
   A: They have different pricing — output tokens cost 5× more than input for Claude. If cost is high, knowing whether it's driven by large context (input) or verbose responses (output) determines the optimization strategy. Trim context vs request shorter responses.

2. **Q: How are metrics stored and why JSON instead of a database?**
   A: Append-only JSON at `data/logs/ai_metrics.json` — each LLM call appends one entry. JSON was chosen because AI metrics are operational/app-level data, not pipeline data. Putting them in the Gold layer would corrupt the IoT data pipeline and fail CI import checks.

3. **Q: How would you set up cost alerting?**
   A: Monitor cumulative `cost_usd` per time window. Alert if daily cost exceeds budget threshold. In production, add a circuit breaker in `ClaudeClient` that stops calls if daily spend exceeds a configured limit.

4. **Q: What's the difference between Claude and Ollama backends?**
   A: Claude is Anthropic's cloud API — fast, reliable, costs money. Ollama runs models locally — free, private, but slower and requires GPU. The `OLLAMA_MODEL` env var (default: llama3) controls which model runs locally. Switching is zero-code — just pull a different model.
