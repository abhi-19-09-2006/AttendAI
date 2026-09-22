"""
PII (Personally Identifiable Information) redaction utilities.

Provides functions to redact sensitive information from logs to prevent
accidental exposure of personal data.
"""
import re
from typing import Optional


def redact_phone(phone: Optional[str]) -> str:
    """
    Redact phone number, showing only last 4 digits.
    
    Args:
        phone: Phone number string
        
    Returns:
        Redacted phone number (e.g., "***-***-1234")
        
    Examples:
        >>> redact_phone("+1-555-123-4567")
        '***-***-4567'
        >>> redact_phone("5551234567")
        '***-***-4567'
        >>> redact_phone("123")
        '123'
        >>> redact_phone(None)
        'N/A'
    """
    if not phone:
        return "N/A"
    
    # Extract only digits
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) < 4:
        return digits
    
    # Show only last 4 digits
    return f"***-***-{digits[-4:]}"


def redact_name(name: Optional[str]) -> str:
    """
    Redact full name, showing only first letter of first name.
    
    Args:
        name: Full name string
        
    Returns:
        Redacted name (e.g., "J***")
        
    Examples:
        >>> redact_name("John Doe")
        'J***'
        >>> redact_name("Jane")
        'J***'
        >>> redact_name("")
        'N/A'
        >>> redact_name(None)
        'N/A'
    """
    if not name or not name.strip():
        return "N/A"
    
    # Take first letter of first word
    first_letter = name.strip()[0].upper()
    return f"{first_letter}***"


def redact_email(email: Optional[str]) -> str:
    """
    Redact email address, showing only domain.
    
    Args:
        email: Email address string
        
    Returns:
        Redacted email (e.g., "***@example.com")
        
    Examples:
        >>> redact_email("user@example.com")
        '***@example.com'
        >>> redact_email("invalid-email")
        'invalid-email'
        >>> redact_email(None)
        'N/A'
    """
    if not email:
        return "N/A"
    
    if '@' not in email:
        return email
    
    _, domain = email.split('@', 1)
    return f"***@{domain}"


def redact_transcript(transcript: Optional[str], max_length: int = 100) -> str:
    """
    Redact transcript for logging, showing only preview.
    
    Args:
        transcript: Full transcript text
        max_length: Maximum length of preview
        
    Returns:
        Redacted transcript preview
        
    Examples:
        >>> redact_transcript("This is a long transcript...")
        '[Transcript: 28 chars]'
        >>> redact_transcript(None)
        '[No transcript]'
    """
    if not transcript:
        return "[No transcript]"
    
    length = len(transcript)
    return f"[Transcript: {length} chars]"


def redact_signature(signature: Optional[str], show_chars: int = 4) -> str:
    """
    Redact HMAC signature, showing only first and last few characters.
    
    Args:
        signature: Full signature string
        show_chars: Number of characters to show at start and end
        
    Returns:
        Redacted signature
        
    Examples:
        >>> redact_signature("abcdef1234567890")
        'abcd...7890'
        >>> redact_signature("short")
        'sh...rt'
        >>> redact_signature(None)
        'N/A'
    """
    if not signature:
        return "N/A"
    
    if len(signature) <= show_chars * 2:
        return signature
    
    return f"{signature[:show_chars]}...{signature[-show_chars:]}"
