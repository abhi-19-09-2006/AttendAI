# AI Transcript Extraction Service - Complete Report

## Overview

A provider-agnostic, LLM-powered extraction service that converts completed phone call transcripts into validated, structured absence information with Pydantic validation, confidence scoring, and automated follow-up triage.

---

## 🎯 Key Capabilities

### 1. Provider-Agnostic Architecture

```
ExtractionProvider (Abstract Base Class)
    ├── OpenAIExtractor (OpenAI GPT-4o with Function Calling)
    └── AnthropicExtractor (Anthropic Claude 3.5 Sonnet with JSON Mode)
```

Factory pattern via `get_extraction_provider()` dynamically loads provider based on `LLM_PROVIDER` environment variable (`openai` or `anthropic`).

### 2. Output Schema (`ExtractedAbsenceInfo`)

```json
{
  "reason": "Not feeling well, has a fever",
  "category": "medical",
  "duration": "2-3 days",
  "expected_return_date": "2026-09-15",
  "parent_confirmed": true,
  "follow_up_required": false,
  "confidence_score": 0.92,
  "confidence_level": "high",
  "notes": "Parent mentioned doctor's appointment tomorrow",
  "parent_statement": "He woke up with a fever around 102",
  "call_outcome": "completed"
}
```

### 3. Core Principles Implemented

- ✅ **Never invent information**: Fields without explicit evidence are strictly `null`/`None`.
- ✅ **Distinguish unknown values**: Explicit `UNKNOWN` category vs missing details.
- ✅ **Confidence scoring**: Granular float `0.0`–`1.0` and derived buckets (`high`, `medium`, `low`, `very_low`).
- ✅ **Automated follow-up trigger**: Automatically forces `follow_up_required=True` when `confidence_score < 0.85` or when notes indicate parent refusal/callback request.
- ✅ **No medical diagnosis**: Preserves parent's raw words without diagnostic speculation.
- ✅ **Exact parent statements preserved**: Captures key quotes under `parent_statement`.
- ✅ **No exposed API keys**: All credentials loaded strictly from environment variables.

---

## 🧪 Tested Scenarios (`backend/tests/test_extraction.py`)

1. **Fever / Illness**: Medical category, high confidence, duration captured, no follow-up needed.
2. **Family Event**: Wedding/trip, family category, expected return date extracted.
3. **Transportation Problem**: Breakdown/commute issue, duration noted.
4. **Parent Refusal**: Private matter / refusal detected, `follow_up_required=True`, confidence `< 0.50`.
5. **Unclear Response**: Vague answers, low confidence, auto-flagged for faculty review.
6. **No Parent Reached / Voicemail**: Zero confidence, `call_outcome="voicemail"`, `follow_up_required=True`.
7. **Multiple Reasons**: Compound cases (e.g. migraine + vehicle trouble) structured appropriately.
8. **Schema Validation & Boundary Tests**: Score clamping, automatic confidence bucket derivation.
9. **Resilience & Fallback**: `AIService` catches `ExtractionError` and provides safe fallback objects with full error tracing.

---

## 📁 Files Created / Modified

- `backend/app/schemas/extraction.py` — Pydantic schema with automated validators and confidence buckets.
- `backend/app/services/extraction_provider.py` — Abstract extraction provider interface.
- `backend/app/services/openai_extractor.py` — OpenAI GPT-4o extractor with function calling and retries.
- `backend/app/services/anthropic_extractor.py` — Anthropic Claude 3.5 Sonnet extractor with JSON schema validation.
- `backend/app/services/extraction_factory.py` — Dynamic provider factory.
- `backend/app/services/ai_service.py` — Refactored high-level AI extraction service.
- `backend/app/services/call_service.py` — Integrated with `ExtractedAbsenceInfo`.
- `backend/tests/test_extraction.py` — 14 comprehensive unit test cases.
