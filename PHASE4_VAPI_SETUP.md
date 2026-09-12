# Phase 4: Vapi Voice Calling Integration - Setup Guide

## Overview

Phase 4 integrates Vapi.ai for AI-powered phone calls to parents about student absences. The system uses a **provider abstraction pattern** to avoid tight coupling to any single voice provider.

---

## Architecture

### Voice Provider Abstraction

```
VoiceProvider (interface)
    ├── VapiProvider (production)
    └── MockVoiceProvider (testing)
```

**Benefits:**
- Provider-agnostic business logic
- Easy to swap providers
- Mockable for testing
- Single reusable assistant configuration

---

## Environment Variables

Add these to your `.env` file:

```bash
# Vapi Configuration
VAPI_API_KEY=your_vapi_api_key_here
VAPI_WEBHOOK_SECRET=your_vapi_webhook_secret_here
VAPI_PHONE_NUMBER_ID=your_phone_number_id_here
VAPI_ASSISTANT_ID=your_assistant_id_here  # Optional: Use pre-created assistant
VAPI_BASE_URL=https://api.vapi.ai

# LLM Provider for Transcript Extraction
LLM_PROVIDER=openai  # or anthropic
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# LLM Models
LLM_EXTRACTION_MODEL=gpt-4o  # For extracting absence info from transcripts
LLM_VOICE_MODEL=gpt-4  # For voice conversations
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500

# Call Configuration
MAX_CALL_DURATION_SECONDS=300
MAX_CALL_RETRIES=3
RETRY_DELAY_MINUTES=30

# Confidence Thresholds
LOW_CONFIDENCE_THRESHOLD=0.7
REQUIRE_REVIEW_THRESHOLD=0.85
```

---

## Vapi Setup

### 1. Get Vapi API Key

1. Sign up at https://vapi.ai
2. Go to Dashboard → Settings → API Keys
3. Create a new API key
4. Copy to `VAPI_API_KEY` in `.env`

### 2. Configure Phone Number

1. In Vapi Dashboard → Phone Numbers
2. Purchase or import a phone number
3. Copy the Phone Number ID to `VAPI_PHONE_NUMBER_ID`

### 3. Setup Webhook (Optional but Recommended)

1. In Vapi Dashboard → Settings → Webhooks
2. Add webhook URL: `https://your-domain.com/webhooks/vapi`
3. Copy the Webhook Secret to `VAPI_WEBHOOK_SECRET`
4. Select events: `call.started`, `call.ended`, `call.failed`, `transcript.ready`

### 4. Create Reusable Assistant (Optional)

Instead of creating an assistant per call, you can create one reusable assistant:

1. In Vapi Dashboard → Assistants → Create Assistant
2. Configure:
   - **Name:** "College Attendance Assistant"
   - **Model:** GPT-4
   - **Voice:** 11labs/rachel (professional female voice)
   - **System Prompt:** Use the template from `vapi_provider.py`
   - **First Message:** Use template variables: `{{studentName}}`, `{{absenceDate}}`
3. Save and copy the Assistant ID to `VAPI_ASSISTANT_ID`

**Note:** If `VAPI_ASSISTANT_ID` is set, the system will use that assistant and override only the student-specific context. Otherwise, it creates an inline assistant configuration per call.

---

## Testing Workflow

### Single Test Call (Before Mass Calling)

**Never begin mass calling without testing first.**

#### Step 1: Prepare Test Data

Ensure you have:
- At least one student in the database
- At least one parent with a valid phone number
- An absence record for today

```bash
# Seed test data if needed
docker-compose exec backend python scripts/seed_data.py
```

#### Step 2: Create Test Absence

Use the API or directly in database:

```bash
POST /api/attendance
{
  "student_id": "student-uuid",
  "date": "2026-09-12",
  "status": "absent"
}
```

#### Step 3: Initiate Test Call

```bash
POST /api/test/test-call
Authorization: Bearer <faculty_token>
{
  "attendance_id": "attendance-uuid"
}
```

Response:
```json
{
  "call_id": "internal-call-uuid",
  "provider_call_id": "vapi-call-id",
  "status": "calling",
  "message": "Test call initiated to +1234567890 for John Smith"
}
```

#### Step 4: Monitor Test Call

```bash
GET /api/test/test-call/{call_id}
```

Response includes:
- Call status (pending, calling, answered, completed, failed)
- Duration
- Absence report (if call completed)
- Confidence score
- Extracted information

#### Step 5: Check Webhook Delivery

View logs to confirm webhooks are being received:

```bash
docker-compose logs -f backend | grep "Received Vapi webhook"
```

---

## API Endpoints

### Test Calls (Faculty Only)

**POST** `/api/test/test-call`
- Create a single test call for an absence
- Body: `{ "attendance_id": "uuid" }`

**GET** `/api/test/test-call/{call_id}`
- Get status and results of test call

### Webhooks (Public)

**POST** `/webhooks/vapi`
- Receives Vapi webhook events
- Verifies signature
- Processes call completion
- Extracts absence information

**GET** `/webhooks/vapi/test`
- Test webhook endpoint reachability

---

## How It Works

### 1. Call Initiation

```python
# Internally uses provider abstraction
call_service = CallService(db)
success = await call_service.initiate_call(call_id)
```

**What happens:**
1. Loads student/parent/absence data
2. Creates `CallContext` with student name, absence date, correlation ID
3. Calls `voice_provider.create_call(context)`
4. Stores provider call ID in database
5. Creates `CallAttempt` record

### 2. During Call

Vapi makes the call using the assistant configuration with:
- Professional greeting mentioning student name and date
- Questions about absence reason
- Expected return date inquiry
- Confirmation and polite closing

### 3. Webhook Processing

When call completes, Vapi sends webhook:

```json
{
  "message": {
    "type": "call.ended"
  },
  "call": {
    "id": "vapi-call-id",
    "status": "completed",
    "metadata": {
      "correlation_id": "our-call-id"
    },
    "transcript": "..."
  }
}
```

**Processing:**
1. Verify webhook signature
2. Parse webhook payload
3. Extract correlation ID (our call ID)
4. Update call status
5. Extract absence info from transcript using LLM
6. Create absence report
7. Create follow-up if needed (low confidence or special cases)

### 4. Information Extraction

The AI service extracts structured data:

```json
{
  "reason": "Not feeling well, has a fever",
  "category": "medical",
  "duration": "2-3 days",
  "expected_return_date": "2026-09-15",
  "parent_confirmed": true,
  "follow_up_required": false,
  "confidence_score": 0.92,
  "notes": "Parent mentioned doctor's appointment tomorrow"
}
```

---

## Security

### API Key Protection

- ✅ API keys stored in environment variables only
- ✅ Never exposed to frontend
- ✅ Webhook signature verification
- ✅ Correlation IDs prevent unauthorized updates

### Webhook Verification

```python
# Verifies X-Vapi-Signature header using HMAC-SHA256
verify_vapi_signature(signature, body)
```

**TODO:** Implement actual HMAC verification in `webhooks.py`

---

## Voice Prompt Design

The assistant uses a **safe, professional prompt**:

✅ Identifies as college attendance assistant
✅ Verifies parent/guardian
✅ Explains the absence clearly
✅ Asks for reason (without prying)
✅ Asks expected return when appropriate
✅ Avoids unnecessary personal information
✅ Never provides medical advice
✅ Confirms information back to parent
✅ Ends politely

**Key guidelines built into prompt:**
- Keep calls under 3 minutes
- Be empathetic and understanding
- Accept general answers ("not feeling well" is sufficient)
- Don't pressure for sensitive medical details
- Offer to call back if parent is busy
- Handle voicemail gracefully

---

## Testing with Mock Provider

For local development without Vapi:

```python
from app.services.mock_provider import MockVoiceProvider

# In tests or local dev
call_service = CallService(db, MockVoiceProvider())

# Simulate outcomes
mock_provider.simulate_answer(call_id, "transcript here")
mock_provider.simulate_no_answer(call_id)
mock_provider.simulate_failed(call_id, "Invalid number")
```

---

## Monitoring

### Call Statistics

```bash
GET /api/calls/statistics
GET /api/calls/statistics?campaign_id=uuid
```

Returns:
- Total calls
- Calls by status
- Average duration
- Success rate

### Logs

```bash
# View call initiation
docker-compose logs -f backend | grep "Initiated call"

# View webhook processing
docker-compose logs -f backend | grep "Vapi webhook"

# View extraction results
docker-compose logs -f backend | grep "confidence"
```

---

## Troubleshooting

### Webhook Not Receiving Events

1. Check webhook URL is publicly accessible (use ngrok for local dev)
2. Verify `VAPI_WEBHOOK_SECRET` matches Vapi dashboard
3. Check firewall/security groups allow Vapi IPs
4. Test with: `GET /webhooks/vapi/test`

### Calls Not Initiating

1. Verify `VAPI_API_KEY` is correct
2. Check `VAPI_PHONE_NUMBER_ID` is valid
3. Ensure phone number is verified in Vapi
4. Check account has sufficient credits
5. Review logs for API errors

### Low Confidence Scores

1. Check transcript quality in logs
2. Verify LLM model is appropriate (gpt-4o recommended)
3. Review extraction prompt in `ai_service.py`
4. Manually review flagged reports: `GET /api/absence-reports?requires_review=true`

### Signature Verification Failing

1. Ensure `VAPI_WEBHOOK_SECRET` is correctly configured
2. Implement HMAC-SHA256 verification (see TODO in `webhooks.py`)
3. Check request headers include `X-Vapi-Signature`

---

## Next Steps

After successful test calls:

1. ✅ **Test single call end-to-end**
2. ✅ **Verify webhook processing**
3. ✅ **Review extracted information accuracy**
4. ⏭️ **Enable call campaigns** (Phase 5)
5. ⏭️ **Add background job queue** (Celery)
6. ⏭️ **Implement call scheduling**
7. ⏭️ **Build retry logic**
8. ⏭️ **Add call analytics dashboard**

---

## Files Created in Phase 4

```
backend/app/services/
  ├── voice_provider.py        # Abstract provider interface
  ├── vapi_provider.py         # Vapi.ai implementation
  ├── vapi_client.py          # Original (replaced by vapi_provider)
  ├── mock_provider.py         # Mock for testing
  ├── ai_service.py            # LLM extraction service
  └── call_service.py          # Updated to use provider abstraction

backend/app/api/
  ├── webhooks.py              # Webhook handler
  └── test_calls.py            # Single test call endpoint

Documentation:
  └── PHASE4_VAPI_SETUP.md     # This file
```

---

## Support

For issues:
1. Check logs: `docker-compose logs -f backend`
2. Review Vapi dashboard for call details
3. Test with mock provider to isolate Vapi issues
4. Verify environment variables are loaded

**Remember: Always test with a single call before enabling mass calling!**
