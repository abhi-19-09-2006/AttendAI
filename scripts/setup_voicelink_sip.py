#!/usr/bin/env python3
"""
VoiceLink SIP Trunk Setup Script for Vapi

This script configures Vapi to use VoiceLink Indian telephony through SIP trunk integration.

What it does:
1. Creates a BYO SIP trunk credential in Vapi with VoiceLink gateway configuration
2. Registers your VoiceLink Indian phone number with that credential
3. Returns the phone number ID to use in AttendAI

Prerequisites:
- VAPI_API_KEY must be set in environment or .env file
- VoiceLink SIP credentials must be available (gateway IP, username, password)
- VoiceLink phone number in E.164 format (e.g., +919876543210)

Usage:
    python scripts/setup_voicelink_sip.py

Environment Variables Required:
    VAPI_API_KEY: Your Vapi API key
    VOICELINK_SIP_GATEWAY_IP: VoiceLink SIP gateway IP or hostname
    VOICELINK_SIP_PORT: SIP port (default: 5060)
    VOICELINK_SIP_USERNAME: SIP authentication username
    VOICELINK_SIP_PASSWORD: SIP authentication password
    VOICELINK_PHONE_NUMBER: Indian phone number in E.164 format
"""

import os
import sys
import json
import httpx
from pathlib import Path

# Add backend to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings


def create_sip_trunk_credential():
    """
    Create a BYO SIP trunk credential in Vapi for VoiceLink.
    
    Returns:
        str: Credential ID if successful, None otherwise
    """
    print("=" * 80)
    print("Step 1: Creating VoiceLink SIP Trunk Credential in Vapi")
    print("=" * 80)
    
    if not settings.VAPI_API_KEY:
        print("❌ ERROR: VAPI_API_KEY is not set")
        return None
    
    if not settings.VOICELINK_SIP_GATEWAY_IP:
        print("❌ ERROR: VOICELINK_SIP_GATEWAY_IP is not set")
        return None
    
    if not settings.VOICELINK_SIP_USERNAME or not settings.VOICELINK_SIP_PASSWORD:
        print("❌ ERROR: VOICELINK_SIP_USERNAME and VOICELINK_SIP_PASSWORD are required")
        return None
    
    payload = {
        "provider": "byo-sip-trunk",
        "name": settings.VOICELINK_SIP_TRUNK_NAME,
        "gateways": [
            {
                "ip": settings.VOICELINK_SIP_GATEWAY_IP,
                "port": settings.VOICELINK_SIP_PORT,
                "inboundEnabled": False,  # Outbound only for now
                "outboundEnabled": True
            }
        ],
        "outboundLeadingPlusEnabled": True,  # Send numbers in E.164 format with +
        "outboundAuthenticationPlan": {
            "authUsername": settings.VOICELINK_SIP_USERNAME,
            "authPassword": settings.VOICELINK_SIP_PASSWORD
        }
    }
    
    print(f"\nConfiguration:")
    print(f"  Trunk Name: {settings.VOICELINK_SIP_TRUNK_NAME}")
    print(f"  Gateway IP: {settings.VOICELINK_SIP_GATEWAY_IP}")
    print(f"  Gateway Port: {settings.VOICELINK_SIP_PORT}")
    print(f"  Username: {settings.VOICELINK_SIP_USERNAME}")
    print(f"  Password: {'*' * len(settings.VOICELINK_SIP_PASSWORD)}")
    print(f"  Outbound E.164: Enabled")
    
    try:
        response = httpx.post(
            f"{settings.VAPI_BASE_URL}/credential",
            headers={
                "Authorization": f"Bearer {settings.VAPI_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30.0
        )
        
        if response.status_code == 201:
            data = response.json()
            credential_id = data.get("id")
            print(f"\n✅ SIP trunk credential created successfully!")
            print(f"   Credential ID: {credential_id}")
            return credential_id
        else:
            print(f"\n❌ Failed to create credential: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"\n❌ Error creating credential: {str(e)}")
        return None


def register_phone_number(credential_id: str):
    """
    Register VoiceLink phone number with the SIP trunk credential.
    
    Args:
        credential_id: The SIP trunk credential ID from step 1
        
    Returns:
        str: Phone number ID if successful, None otherwise
    """
    print("\n" + "=" * 80)
    print("Step 2: Registering VoiceLink Phone Number in Vapi")
    print("=" * 80)
    
    if not settings.VOICELINK_PHONE_NUMBER:
        print("❌ ERROR: VOICELINK_PHONE_NUMBER is not set")
        return None
    
    # Validate E.164 format
    if not settings.VOICELINK_PHONE_NUMBER.startswith("+"):
        print(f"⚠️  WARNING: Phone number should be in E.164 format (e.g., +919876543210)")
        print(f"   Current value: {settings.VOICELINK_PHONE_NUMBER}")
        print(f"   Attempting to use as-is...")
    
    payload = {
        "provider": "byo-phone-number",
        "name": f"VoiceLink India - {settings.VOICELINK_PHONE_NUMBER}",
        "number": settings.VOICELINK_PHONE_NUMBER,
        "numberE164CheckEnabled": False,  # Allow non-standard formats if needed
        "credentialId": credential_id
    }
    
    print(f"\nConfiguration:")
    print(f"  Phone Number: {settings.VOICELINK_PHONE_NUMBER}")
    print(f"  Credential ID: {credential_id}")
    
    try:
        response = httpx.post(
            f"{settings.VAPI_BASE_URL}/phone-number",
            headers={
                "Authorization": f"Bearer {settings.VAPI_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30.0
        )
        
        if response.status_code == 201:
            data = response.json()
            phone_number_id = data.get("id")
            print(f"\n✅ Phone number registered successfully!")
            print(f"   Phone Number ID: {phone_number_id}")
            return phone_number_id
        else:
            print(f"\n❌ Failed to register phone number: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"\n❌ Error registering phone number: {str(e)}")
        return None


def update_env_file(phone_number_id: str):
    """
    Update .env file with the new phone number ID.
    
    Args:
        phone_number_id: The phone number ID to set
    """
    print("\n" + "=" * 80)
    print("Step 3: Updating Environment Configuration")
    print("=" * 80)
    
    env_file = Path(__file__).parent.parent / ".env"
    
    if not env_file.exists():
        print(f"⚠️  .env file not found at {env_file}")
        print(f"   Please manually set VAPI_PHONE_NUMBER_ID={phone_number_id}")
        return
    
    # Read existing .env
    lines = env_file.read_text().splitlines()
    
    # Update VAPI_PHONE_NUMBER_ID
    updated = False
    for i, line in enumerate(lines):
        if line.startswith("VAPI_PHONE_NUMBER_ID="):
            lines[i] = f"VAPI_PHONE_NUMBER_ID={phone_number_id}"
            updated = True
            break
    
    if not updated:
        # Add it if not present
        lines.append(f"VAPI_PHONE_NUMBER_ID={phone_number_id}")
    
    # Write back
    env_file.write_text("\n".join(lines) + "\n")
    
    print(f"✅ Updated .env file:")
    print(f"   VAPI_PHONE_NUMBER_ID={phone_number_id}")


def main():
    """Main setup flow."""
    print("\n" + "=" * 80)
    print("VoiceLink SIP Trunk Setup for Vapi")
    print("AttendAI - Indian Telephony Integration")
    print("=" * 80)
    
    # Step 1: Create SIP trunk credential
    credential_id = create_sip_trunk_credential()
    if not credential_id:
        print("\n❌ Setup failed at Step 1. Please check the errors above.")
        sys.exit(1)
    
    # Step 2: Register phone number
    phone_number_id = register_phone_number(credential_id)
    if not phone_number_id:
        print("\n❌ Setup failed at Step 2. Please check the errors above.")
        sys.exit(1)
    
    # Step 3: Update .env file
    update_env_file(phone_number_id)
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ VoiceLink SIP Trunk Setup Complete!")
    print("=" * 80)
    print(f"\nConfiguration Summary:")
    print(f"  SIP Trunk Credential ID: {credential_id}")
    print(f"  Phone Number ID: {phone_number_id}")
    print(f"  Phone Number: {settings.VOICELINK_PHONE_NUMBER}")
    print(f"\nNext Steps:")
    print(f"  1. Restart your AttendAI backend to load the new VAPI_PHONE_NUMBER_ID")
    print(f"  2. Test a call using the staging test script:")
    print(f"     ./scripts/vapi_staging_test.sh")
    print(f"  3. Verify the caller ID shows your VoiceLink Indian number")
    print(f"\nTroubleshooting:")
    print(f"  - If calls fail, check VoiceLink SIP trunk status in their dashboard")
    print(f"  - Verify SIP credentials are correct")
    print(f"  - Ensure VoiceLink gateway IP is reachable from Vapi servers")
    print(f"  - Check Vapi dashboard for the registered phone number")
    print("=" * 80)


if __name__ == "__main__":
    main()
