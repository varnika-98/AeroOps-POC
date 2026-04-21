# prompts.py

> File: `ai/prompts.py`

## Overview

Prompt engineering templates for all LLM interactions. Defines the system persona, structured output format, and task-specific instructions for diagnosis, recommendations, and chat. This is the "personality and behavior" layer of the AI system.

## Purpose

- **Consistent persona** — All responses maintain the "AeroOps AI operations assistant" identity
- **Output structure** — Enforces structured incident analysis format
- **Grounding enforcement** — Explicit instructions to never fabricate metrics
- **Task specialization** — Different prompts for different use cases (diagnose vs chat)
- **Separation of concerns** — Prompts live separately from client logic for easy iteration

## Prompt Templates

### SYSTEM_PROMPT

**Role:** Airport data pipeline operations analyst

**Key instructions:**
1. **GROUNDED** — Only reference data in provided context, never fabricate
2. **SPECIFIC** — Name exact streams, sensors, timestamps, KPI values
3. **ACTIONABLE** — Every diagnosis includes concrete next steps
4. **STRUCTURED** — Use format: What changed → What broke → What's impacted → Recommended action

**Domain knowledge declared:**
- Medallion architecture (Bronze/Silver/Gold)
- Data quality rules and validation
- Pipeline orchestration
- IoT sensor networks
- 6 streams: flights, passengers, cargo, environmental, runway, security

### DIAGNOSIS_PROMPT

**Purpose:** Incident analysis when user clicks "Generate System Diagnosis"

**Template structure:**
```
[Instructions for root cause analysis]

=== SYSTEM CONTEXT ===
{context}              ← Injected by context_builder
=== END CONTEXT ===

Provide your analysis now.
```

**Expected output format per issue:**
1. Clear description of what is happening
2. Most likely root cause
3. Which Gold-layer KPIs and dashboards are affected
4. Specific remediation steps

### RECOMMENDATION_PROMPT

**Purpose:** Optimization suggestions when user clicks "Get Recommendations"

**Template structure:**
```
[Instructions for optimization recommendations]
[Prioritize by impact × effort matrix]

=== SYSTEM CONTEXT ===
{context}
=== END CONTEXT ===

{question}             ← Optional focus area
```

**Expected output:** Prioritized list with impact (high/medium/low) and effort (quick-win/moderate/major)

### CHAT_PROMPT

**Purpose:** Interactive Q&A grounded in system data

**Template structure:**
```
[Instructions: answer from context, don't speculate]

=== SYSTEM CONTEXT ===
{context}
=== END CONTEXT ===

User question: {question}
```

**Key constraint:** "If the context does not contain enough information to answer, say so clearly."

## Prompt Engineering Principles Applied

| Principle | Implementation |
|-----------|---------------|
| Role assignment | "You are AeroOps AI, an intelligent operations assistant" |
| Output format specification | "Use this format: What changed / What broke / What's impacted / Action" |
| Grounding constraint | "Only reference data provided in context. Never fabricate." |
| Domain anchoring | Lists all streams, architecture patterns, and expected vocabulary |
| Context boundaries | `=== SYSTEM CONTEXT ===` delimiters prevent prompt injection |
| Specificity instruction | "Name exact streams, sensors, timestamps, and KPI values" |
| Fallback behavior | "If context doesn't contain enough info, say so clearly" |

## How Templates Are Used

```python
# In claude_client.py:

# Diagnosis (single-turn)
prompt = DIAGNOSIS_PROMPT.format(context=context_text)
response = client.messages.create(system=SYSTEM_PROMPT, messages=[{"role": "user", "content": prompt}])

# Chat (multi-turn, context in first message only)
grounded = CHAT_PROMPT.format(context=context_text, question=first_message)
messages = [{"role": "user", "content": grounded}, ...rest of history...]
response = client.messages.create(system=SYSTEM_PROMPT, messages=messages)
```

## Interview Q&A

1. **Q: Why separate system prompt from task prompts?**
   A: The system prompt sets persistent behavior (persona, constraints, format) across all interactions. Task prompts define what to do with a specific context. This mirrors the Anthropic API design where `system` is a separate parameter from `messages`. Changing diagnosis logic doesn't affect chat behavior.

2. **Q: How do the context delimiters (`=== SYSTEM CONTEXT ===`) help?**
   A: They create clear boundaries between instructions and data. The LLM learns to treat content between delimiters as reference material, not as instructions to follow. This prevents prompt injection — if quarantine data contained "ignore previous instructions," the delimiters help the LLM treat it as data.

3. **Q: Why enforce structured output ("What changed / What broke / What's impacted")?**
   A: Structure ensures completeness — without it, the LLM might describe the problem without suggesting remediation. It also makes responses scannable for operators under pressure. Consistent format enables future parsing for automated alerting.

4. **Q: How would you iterate on prompts in production?**
   A: A/B testing — serve different prompt versions to different sessions, track response quality scores (user thumbs up/down). Store prompt versions with their metrics. Use the winning version. Tools like LangSmith or Braintrust enable this workflow.

5. **Q: Why is "never fabricate" the #1 rule?**
   A: In operations, wrong data is worse than no data. If the AI says "flight OTP is 45%" when it's actually 87%, operators waste time investigating a non-existent problem. The grounding constraint forces the LLM to say "I don't have that information" rather than guess — which is the safe behavior for critical systems.
