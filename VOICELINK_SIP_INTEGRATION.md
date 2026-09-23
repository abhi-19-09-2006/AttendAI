# VoiceLink SIP Integration for AttendAI

This guide explains how to configure Vapi to use VoiceLink Indian telephony through SIP trunk integration, replacing the free Vapi phone number with a real Indian phone number.

## Overview

**What This Does:**
- Keeps Vapi as the AI voice agent (no changes to AI logic)
- Replaces Vapi's free phone number with VoiceLink Indian telephony
- Uses Vapi's BYO (Bring Your Own) SIP trunk integration
- Maintains all existing AttendAI application logic (RQ, webhooks, transcripts, etc.)

**What Changes:**
- Only the telephony layer: Vapi now routes calls through VoiceLink SIP trunk
- Caller ID will show your VoiceLink Indian number instead of Vapi's number

**What Stays the Same:**
- Vapi assistant configuration
- Call initiation flow (RQ jobs)
- Webhook processing
- Transcript extraction
- Follow-up logic
- Database models
- E.164 phone normalization

---

## Prerequisites

### 1. VoiceLink Account & Credentials

You need the following from VoiceLink:

| Credential | Description | Example |
|------------|-------------|---------|
| **SIP Gateway IP/Hostname** | VoiceLink's SIP server address | `sip.voicelink.in` or `103.xx.xx.xx` |
| **SIP Port** | SIP signaling port | `5060` (default) |
| **SIP Username** | Authentication username | `919876543210` or `user123` |
| **SIP Password** | Authentication password | `your_password` |
| **Phone Number** | Your Indian DID in E.164 format | `+919876543210` |

**How to Get These:**
1. Log into your VoiceLink dashboard
2. Navigate to **SIP Trunking** or **SIP Credentials** section
3. Create or view your SIP trunk credentials
4. Note down the gateway IP, username, and password
5. Ensure your phone number is provisioned and active

### 2. Vapi Account

- Active Vapi account with API access
- Vapi API key (from Organization Settings)
- Sufficient credits for outbound calls

---

## Configuration Steps

### Step 1: Set Environment Variables

Add these to your `.env` file (or `.env.staging` / `.env.prod`):

```bash
# Existing Vapi Configuration
VAPI_API_KEY=your_vapi_api_key_here
VAPI_WEBHOOK_SECRET=your_webhook_secret_here
VAPI_BASE_URL=https://api.vapi.ai

# VoiceLink SIP Configuration (NEW)
VOICELINK_SIP_GATEWAY_IP=sip.voicelink.in
VOICELINK_SIP_PORT=5060
VOICELINK_SIP_USERNAME=919876543210
VOICELINK_SIP_PASSWORD=your_voicelink_password
VOICELINK_PHONE_NUMBER=+919876543210
VOICELINK_SIP_TRUNK_NAME=VoiceLink India Trunk
```

**Important:**
- `VOICELINK_PHONE_NUMBER` must be in E.164 format: `+91` + 10 digits
- `VOICELINK_SIP_GATEWAY_IP` can be a hostname or IP address
- Keep `VOICELINK_SIP_PASSWORD` secure - never commit to git

### Step 2: Run the Setup Script

The setup script will:
1. Create a SIP trunk credential in Vapi
2. Register your VoiceLink phone number with that credential
3. Update your `.env` file with the new `VAPI_PHONE_NUMBER_ID`

```bash
cd /home/user/AttendAI
python scripts/setup_voicelink_sip.py
```

**Expected Output:**
```
================================================================================
Step 1: Creating VoiceLink SIP Trunk Credential in Vapi
================================================================================

Configuration:
  Trunk Name: VoiceLink India Trunk
  Gateway IP: sip.voicelink.in
  Gateway Port: 5060
  Username: 919876543210
  Password: ****************
  Outbound E.164: Enabled

✅ SIP trunk credential created successfully!
   Credential ID: cred_abc123def456

================================================================================
Step 2: Registering VoiceLink Phone Number in Vapi
================================================================================

Configuration:
  Phone Number: +919876543210
  Credential ID: cred_abc123def456

✅ Phone number registered successfully!
   Phone Number ID: phone_xyz789ghi012

================================================================================
Step 3: Updating Environment Configuration
================================================================================
✅ Updated .env file:
   VAPI_PHONE_NUMBER_ID=phone_xyz789ghi012

================================================================================
✅ VoiceLink SIP Trunk Setup Complete!
================================================================================
```

### Step 3: Restart AttendAI Backend

```bash
# For staging
docker compose -f docker-compose.staging.yml restart backend worker

# For production
docker compose -f docker-compose.prod.yml restart backend worker
```

### Step 4: Verify Configuration

**Check Vapi Dashboard:**
1. Log into [Vapi Dashboard](https://dashboard.vapi.ai)
2. Navigate to **Phone Numbers** section
3. Verify your VoiceLink number appears with status "Active"
4. Check **Credentials** section - you should see "VoiceLink India Trunk"

**Check AttendAI Logs:**
```bash
# Staging
docker compose -f docker-compose.staging.yml logs backend | grep -i vapi

# Should show successful initialization
```

---

## Manual Configuration (Alternative)

If you prefer to configure manually instead of using the script:

### 1. Create SIP Trunk Credential via API

```bash
curl -X POST https://api.vapi.ai/credential \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_VAPI_API_KEY" \
  -d '{
    "provider": "byo-sip-trunk",
    "name": "VoiceLink India Trunk",
    "gateways": [
      {
        "ip": "sip.voicelink.in",
        "port": 5060,
        "inboundEnabled": false,
        "outboundEnabled": true
      }
    ],
    "outboundLeadingPlusEnabled": true,
    "outboundAuthenticationPlan": {
      "authUsername": "919876543210",
      "authPassword": "your_voicelink_password"
    }
  }'
```

**Response:**
```json
{
  "id": "cred_abc123def456",
  "provider": "byo-sip-trunk",
  "name": "VoiceLink India Trunk",
  ...
}
```

**Note the `id` field** - you'll need it for the next step.

### 2. Register Phone Number via API

```bash
curl -X POST https://api.vapi.ai/phone-number \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_VAPI_API_KEY" \
  -d '{
    "provider": "byo-phone-number",
    "name": "VoiceLink India - +919876543210",
    "number": "+919876543210",
    "numberE164CheckEnabled": false,
    "credentialId": "cred_abc123def456"
  }'
```

**Response:**
```json
{
  "id": "phone_xyz789ghi012",
  "provider": "byo-phone-number",
  "number": "+919876543210",
  ...
}
```

**Note the `id` field** - this is your `VAPI_PHONE_NUMBER_ID`.

### 3. Update `.env` File

```bash
VAPI_PHONE_NUMBER_ID=phone_xyz789ghi012
```

### 4. Restart Backend

```bash
docker compose -f docker-compose.staging.yml restart backend worker
```

---

## Vapi Dashboard Configuration (GUI Alternative)

If you prefer using the Vapi dashboard instead of API:

### 1. Create SIP Trunk Credential

1. Log into [Vapi Dashboard](https://dashboard.vapi.ai)
2. Navigate to **Credentials** → **Create Credential**
3. Select **BYO SIP Trunk**
4. Fill in:
   - **Name**: `VoiceLink India Trunk`
   - **Gateway IP**: `sip.voicelink.in`
   - **Gateway Port**: `5060`
   - **Outbound Enabled**: ✅ Yes
   - **Inbound Enabled**: ❌ No (unless you need inbound calls)
   - **Authentication**: Username/Password
   - **Username**: `919876543210`
   - **Password**: `your_voicelink_password`
   - **Outbound Leading Plus**: ✅ Enabled
5. Click **Create**
6. Copy the **Credential ID**

### 2. Add Phone Number

1. Navigate to **Phone Numbers** → **Add Phone Number**
2. Select **BYO Phone Number**
3. Fill in:
   - **Name**: `VoiceLink India - +919876543210`
   - **Number**: `+919876543210`
   - **Credential**: Select "VoiceLink India Trunk"
   - **E.164 Check**: Disabled (if needed)
4. Click **Add**
5. Copy the **Phone Number ID**

### 3. Update `.env` File

```bash
VAPI_PHONE_NUMBER_ID=phone_xyz789ghi012
```

---

## Testing

### 1. Test Configuration (No Real Call)

```bash
cd /home/user/AttendAI/backend
python -m pytest tests/test_voice_services.py::test_vapi_create_call_normalizes_phone -v
```

This verifies the payload structure without making a real call.

### 2. Test Staging Call (Real Call)

**⚠️ WARNING: This will make a real phone call!**

```bash
cd /home/user/AttendAI
export STAGING_TEST_NUMBER="+91YOUR_TEST_NUMBER"
export AUTH_TOKEN="your_jwt_token"
./scripts/vapi_staging_test.sh
```

**What to Verify:**
- Call initiates successfully
- Caller ID shows your VoiceLink number (+919876543210)
- Call connects and AI assistant speaks
- Transcript is captured in webhook
- Call status updates correctly

---

## Troubleshooting

### Issue: "Invalid credential ID"

**Cause:** The `VAPI_PHONE_NUMBER_ID` in `.env` doesn't match a valid phone number in Vapi.

**Solution:**
1. Check Vapi dashboard → Phone Numbers
2. Verify the phone number exists and is active
3. Copy the correct ID and update `.env`
4. Restart backend

### Issue: "SIP registration failed"

**Cause:** VoiceLink SIP credentials are incorrect or gateway is unreachable.

**Solution:**
1. Verify SIP username/password in VoiceLink dashboard
2. Check if VoiceLink gateway IP is correct
3. Test SIP registration from VoiceLink side
4. Ensure VoiceLink account has sufficient balance

### Issue: "Call failed with 400 Bad Request"

**Cause:** Phone number format or SIP trunk configuration issue.

**Solution:**
1. Verify `VOICELINK_PHONE_NUMBER` is in E.164 format: `+919876543210`
2. Check Vapi dashboard → Phone Numbers → your number → status
3. Verify SIP trunk credential is active
4. Check Vapi logs for detailed error message

### Issue: "Calls work but caller ID is wrong"

**Cause:** VoiceLink not configured to pass caller ID, or Vapi not sending it correctly.

**Solution:**
1. Check VoiceLink dashboard → Caller ID settings
2. Ensure your DID is allowed as caller ID
3. Verify `outboundLeadingPlusEnabled: true` in SIP trunk credential
4. Check Vapi call logs for outbound SIP headers

### Issue: "No audio / one-way audio"

**Cause:** NAT/firewall issues between Vapi and VoiceLink SIP servers.

**Solution:**
1. Check if VoiceLink requires specific codec (G.711, G.729)
2. Verify RTP ports are open (typically 10000-20000)
3. Check if VoiceLink needs IP whitelisting for Vapi servers
4. Contact VoiceLink support for SIP trunk troubleshooting

---

## VoiceLink-Specific Configuration

### VoiceLink Dashboard Settings

**SIP Trunk Configuration:**
- **Protocol**: UDP (default) or TCP
- **Codec**: G.711u (PCMU) preferred, G.711a (PCMA) also supported
- **DTMF**: RFC 2833
- **Fax**: T.38 (if needed)
- **SRTP**: Optional (Vapi supports it)

**Caller ID Settings:**
- Ensure your DID is set as default caller ID
- Verify caller ID is not blocked or restricted
- Check if VoiceLink requires caller ID verification

**Billing:**
- VoiceLink charges per minute for outbound calls
- Check your balance before testing
- Monitor usage in VoiceLink dashboard

### VoiceLink Support

If you encounter VoiceLink-specific issues:
- **Dashboard**: [VoiceLink Portal](https://portal.voicelink.in)
- **Support Email**: support@voicelink.in
- **Support Phone**: +91-xxxx-xxxxxx
- **Documentation**: [VoiceLink SIP Trunk Guide](https://voicelink.in/docs/sip-trunk)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      AttendAI Backend                        │
│                                                              │
│  ┌──────────────┐         ┌──────────────────────────────┐  │
│  │   RQ Worker  │────────▶│     VapiProvider              │  │
│  │              │         │  (app/services/vapi_provider) │  │
│  └──────────────┘         └──────────────────────────────┘  │
│                                    │                         │
│                                    │ HTTP POST /call         │
│                                    │ - phoneNumberId         │
│                                    │ - customer.number       │
│                                    │ - assistant config      │
└────────────────────────────────────┼─────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────┐
│                        Vapi Platform                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Phone Number: +919876543210                          │   │
│  │  Credential: VoiceLink India Trunk (cred_xxx)         │   │
│  │  Provider: byo-phone-number                           │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          │ SIP INVITE                        │
│                          │ (via SIP trunk)                   │
└──────────────────────────┼───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    VoiceLink SIP Trunk                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Gateway: sip.voicelink.in:5060                       │   │
│  │  Auth: 919876543210 / password                        │   │
│  │  Caller ID: +919876543210                             │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          │ PSTN                              │
└──────────────────────────┼───────────────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Customer   │
                    │    Phone     │
                    └──────────────┘
```

---

## Security Considerations

### 1. SIP Credentials

- **Never commit** `VOICELINK_SIP_PASSWORD` to git
- Use `.env` files (already in `.gitignore`)
- Rotate credentials periodically
- Use strong passwords

### 2. API Keys

- Keep `VAPI_API_KEY` secure
- Use different keys for staging/production
- Rotate if compromised

### 3. Network Security

- VoiceLink SIP traffic is unencrypted by default (UDP 5060)
- Consider enabling TLS/SRTP if VoiceLink supports it
- Whitelist Vapi IPs in VoiceLink firewall if possible

### 4. Compliance

- Ensure VoiceLink usage complies with TRAI regulations
- Follow Indian telecom guidelines for automated calls
- Maintain call records for compliance

---

## Cost Estimation

### VoiceLink Pricing (Example)

- **Outbound Calls**: ₹0.50 per minute (check current rates)
- **DID Rental**: ₹100 per month
- **SIP Trunk**: Free (included with DID)

### Vapi Pricing

- **AI Processing**: $0.05 per minute
- **Telephony**: Not charged (using your own trunk)

### Total Cost Per Call (3 minutes)

- VoiceLink: ₹1.50
- Vapi: $0.15 (~₹12.50)
- **Total**: ~₹14 per call

---

## Rollback Plan

If you need to revert to Vapi's free phone number:

1. **Get Vapi Phone Number ID:**
   - Log into Vapi dashboard
   - Navigate to Phone Numbers
   - Find the Vapi-provided number
   - Copy its ID

2. **Update `.env`:**
   ```bash
   VAPI_PHONE_NUMBER_ID=vapi_phone_xxx
   ```

3. **Restart Backend:**
   ```bash
   docker compose -f docker-compose.staging.yml restart backend worker
   ```

---

## Support & Resources

### Vapi Documentation
- [SIP Trunk Integration](https://docs.vapi.ai/advanced/sip/custom)
- [BYO Phone Number](https://docs.vapi.ai/phone-numbers/byo-phone-number)
- [API Reference](https://docs.vapi.ai/api-reference)

### VoiceLink Documentation
- [SIP Trunk Setup](https://voicelink.in/docs/sip-trunk)
- [API Documentation](https://voicelink.in/docs/api)
- [Support Portal](https://support.voicelink.in)

### AttendAI Documentation
- [Phase 13: Vapi Integration](../PHASE_13_VAPI_INTEGRATION.md)
- [Phase 18: Staging Release](../PHASE_18_STAGING_RELEASE.md)
- [Deployment Guide](../DEPLOYMENT.md)

---

## Checklist

Before going live with VoiceLink:

- [ ] VoiceLink SIP credentials obtained and tested
- [ ] Environment variables configured in `.env.staging`
- [ ] Setup script run successfully
- [ ] `VAPI_PHONE_NUMBER_ID` updated in `.env`
- [ ] Backend restarted
- [ ] Vapi dashboard shows active phone number
- [ ] Test call made successfully
- [ ] Caller ID verified as VoiceLink number
- [ ] Transcript captured correctly
- [ ] Webhook processing works
- [ ] Call status updates correctly
- [ ] VoiceLink balance sufficient
- [ ] Monitoring/alerting configured
- [ ] Rollback plan documented
- [ ] Team trained on new telephony setup

---

**Last Updated:** 2026-09-23  
**Maintained By:** AttendAI DevOps Team
