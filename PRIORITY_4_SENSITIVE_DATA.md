# Priority 4: Sensitive Data Protection - Design Document

**Date**: September 14, 2026  
**Status**: Design Phase  
**Implementation**: Phase 9 (Future)

---

## Current State Analysis

### Sensitive Data Inventory

| Field | Model | Type | Current Storage | Sensitivity | PII | Risk |
|-------|-------|------|-----------------|-------------|-----|------|
| primary_phone | Parent | String(20) | Plaintext | HIGH | ✅ Yes | CRITICAL |
| secondary_phone | Parent | String(20) | Plaintext | MEDIUM | ✅ Yes | HIGH |
| email | Parent | String(255) | Plaintext | MEDIUM | ✅ Yes | MEDIUM* |
| transcript | AbsenceReport | Text | Plaintext | HIGH | ✅ Yes (content) | CRITICAL |
| raw_extraction | AbsenceReport | JSON | Plaintext | HIGH | ✅ Yes (content) | CRITICAL |
| reason | AbsenceReport | Text | Plaintext | MEDIUM | ❌ No | MEDIUM |
| voice_url | Call | String | S3 with 30d TTL | HIGH | ✅ Yes (audio) | HIGH |

*Email is less sensitive (widely shared in directory services)

---

## Compliance Requirements

### FERPA (Family Educational Rights and Privacy Act)
- ✅ Student records must be protected
- ✅ Parents can access their child's records only
- ✅ Staff access must be logged
- ⚠️ Data retention must be configurable

### CCPA (California Consumer Privacy Act)
- ✅ Consumers can request deletion
- ✅ Data cannot be sold
- ✅ Security must be reasonable

### Best Practices
- ✅ Encrypt sensitive PII at rest
- ✅ Encrypt in transit (HTTPS)
- ✅ Access control by role and relationship
- ✅ Audit logging for sensitive data access
- ✅ Data retention policies

---

## Proposed Solution: Multi-Layer Protection

### Layer 1: Encryption at Rest

**Approach**: SQLAlchemy Hybrid Properties with AES-256-GCM

```python
from sqlalchemy import String
from sqlalchemy.ext.hybrid import hybrid_property
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import base64

class Parent(Base):
    """Parent model with encrypted phone numbers."""
    
    _primary_phone_encrypted = Column(String, nullable=True)
    _primary_phone_nonce = Column(String, nullable=True)
    
    def _encrypt_phone(self, phone: str) -> tuple[str, str]:
        """Encrypt phone number using AES-256-GCM."""
        if not phone:
            return None, None
        
        key = base64.b64decode(settings.DATA_ENCRYPTION_KEY)
        nonce = os.urandom(12)
        cipher = AESGCM(key)
        
        ciphertext = cipher.encrypt(nonce, phone.encode(), None)
        
        return (
            base64.b64encode(ciphertext).decode(),
            base64.b64encode(nonce).decode()
        )
    
    def _decrypt_phone(self, ciphertext: str, nonce: str) -> str:
        """Decrypt phone number."""
        if not ciphertext or not nonce:
            return None
        
        key = base64.b64decode(settings.DATA_ENCRYPTION_KEY)
        cipher = AESGCM(key)
        
        plaintext = cipher.decrypt(
            base64.b64decode(nonce),
            base64.b64decode(ciphertext),
            None
        )
        
        return plaintext.decode()
    
    @hybrid_property
    def primary_phone(self) -> str:
        """Get decrypted primary phone."""
        if self._primary_phone_encrypted is None:
            return None
        return self._decrypt_phone(self._primary_phone_encrypted, self._primary_phone_nonce)
    
    @primary_phone.setter
    def primary_phone(self, value: str):
        """Set and encrypt primary phone."""
        if value:
            encrypted, nonce = self._encrypt_phone(value)
            self._primary_phone_encrypted = encrypted
            self._primary_phone_nonce = nonce
        else:
            self._primary_phone_encrypted = None
            self._primary_phone_nonce = None
```

**Benefits**:
- Transparent to application code (queries return decrypted values)
- Database stores only ciphertext
- If database is compromised, data remains protected
- Key is in environment (never in code)

**Performance**:
- Encryption: ~5ms per field
- Decryption: ~5ms per field
- Acceptable for most use cases
- Cache decrypted values if needed

### Layer 2: Access Control

**Row-Level Access Control (RLAC)**

```python
class AccessControl:
    """Enforce RLAC for sensitive data."""
    
    @staticmethod
    async def can_access_student(user: User, student: Student) -> bool:
        """Check if user can access student."""
        if user.role == "ADMIN":
            return True
        
        if user.role == "FACULTY":
            # Faculty can access their students
            return await db.query(Enrollment).filter(
                Enrollment.faculty_id == user.id,
                Enrollment.student_id == student.id
            ).first() is not None
        
        if user.role == "STAFF":
            # Staff can access any student
            return True
        
        if user.role == "PARENT":
            # Parents can only access their own children
            return await db.query(StudentParent).filter(
                StudentParent.parent_id == user.id,
                StudentParent.student_id == student.id
            ).first() is not None
        
        return False
    
    @staticmethod
    async def can_access_parent_data(user: User, parent: Parent, student: Student) -> bool:
        """Check if user can access parent contact data."""
        # Must be able to access student first
        if not await AccessControl.can_access_student(user, student):
            return False
        
        # ADMIN can access everything
        if user.role == "ADMIN":
            return True
        
        # FACULTY can access parent contact info for their students
        if user.role == "FACULTY":
            return True
        
        # STAFF cannot access parent phone numbers (only faculty can)
        if user.role == "STAFF":
            return False
        
        # Parents can only access their own info
        if user.role == "PARENT":
            return parent.id == user.id or any(
                child.id == student.id
                for child in await parent.get_children()
            )
        
        return False
    
    @staticmethod
    async def can_access_transcript(user: User, report: AbsenceReport) -> bool:
        """Check if user can access call transcript."""
        student = await report.get_student()
        
        if not await AccessControl.can_access_student(user, student):
            return False
        
        # Transcripts are sensitive - only ADMIN and calling FACULTY
        if user.role == "ADMIN":
            return True
        
        if user.role == "FACULTY":
            # Only faculty who initiated the call
            call = await report.get_call()
            return call.initiated_by_id == user.id
        
        # Parents cannot access transcripts (privacy)
        return False
```

### Layer 3: Data Masking in API Responses

**Selective Field Masking**

```python
class ParentSchema(BaseModel):
    """Parent schema with masking rules."""
    
    id: int
    first_name: str
    last_name: str
    email: str
    primary_phone: str | None = None
    secondary_phone: str | None = None
    
    @field_serializer('primary_phone', 'secondary_phone')
    def mask_phone(self, value: str, _info: SerializationInfo) -> str | None:
        """Mask phone numbers based on access level."""
        if not value:
            return None
        
        # Get current user from context
        user = get_current_user()
        
        # Admin sees full number
        if user.role == "ADMIN":
            return value
        
        # Faculty sees partial (XXX-XXX-1234)
        if user.role == "FACULTY":
            return f"***-***-{value[-4:]}"
        
        # Others see nothing
        return None
    
    class Config:
        # Only serialize fields explicitly allowed
        fields = {
            'primary_phone': {'exclude': False},  # Controlled by serializer
            'secondary_phone': {'exclude': False},
        }
```

### Layer 4: Data Retention & Deletion

**Retention Policy**

```python
class DataRetention:
    """Implement data retention policies."""
    
    @staticmethod
    async def cleanup_old_data():
        """Delete data older than retention period."""
        now = datetime.utcnow()
        
        # Delete transcripts older than 90 days
        await db.delete(
            AbsenceReport
        ).where(
            AbsenceReport.created_at < (now - timedelta(days=90)),
            AbsenceReport.transcript.isnot(None)
        )
        
        # Delete call recordings older than 30 days (S3 TTL handles this)
        # Just clean up DB records
        await db.delete(
            Call
        ).where(
            Call.completed_at < (now - timedelta(days=30)),
            Call.status == "completed"
        )
        
        await db.commit()
```

**Deletion Request (CCPA)**

```python
@router.post("/api/data/delete-my-data")
async def request_data_deletion(
    current_user: User = Depends(get_current_user)
):
    """Request data deletion for current user (CCPA)."""
    
    # Create deletion request
    deletion = DataDeletionRequest(
        user_id=current_user.id,
        status="pending",
        requested_at=datetime.utcnow()
    )
    db.add(deletion)
    
    # Mark all sensitive data for deletion
    if current_user.role == "PARENT":
        parent = await get_parent(current_user.id)
        parent.primary_phone = None
        parent.secondary_phone = None
    
    await db.commit()
    
    return {
        "message": "Deletion request submitted",
        "request_id": deletion.id,
        "status": "pending"
    }
```

---

## Implementation Plan

### Phase 9A: Database Schema Changes

**New Columns** (add to existing models without dropping data):

```python
# Parent model
class Parent(Base):
    primary_phone = Column(String(20))  # Keep for backward compat
    _primary_phone_encrypted = Column(String)  # New encrypted column
    _primary_phone_nonce = Column(String)
    
    secondary_phone = Column(String(20))  # Keep for backward compat
    _secondary_phone_encrypted = Column(String)  # New encrypted column
    _secondary_phone_nonce = Column(String)

# AbsenceReport model
class AbsenceReport(Base):
    transcript = Column(Text)  # Keep for backward compat
    _transcript_encrypted = Column(Text)  # New encrypted column
    _transcript_nonce = Column(String)
    
    raw_extraction = Column(JSON)  # Keep for backward compat
    _raw_extraction_encrypted = Column(Text)  # New encrypted column
    _raw_extraction_nonce = Column(String)
```

**Migration**:
```python
# Alembic migration
def upgrade():
    op.add_column('parent', Column('_primary_phone_encrypted', String))
    op.add_column('parent', Column('_primary_phone_nonce', String))
    # ... repeat for other fields ...

def downgrade():
    op.drop_column('parent', '_primary_phone_encrypted')
    # ... reverse ...
```

**Data Migration Script**:
```python
async def migrate_to_encrypted():
    """Encrypt existing plaintext data."""
    encryption = DataEncryption()
    
    # Migrate parent phone numbers
    parents = await db.query(Parent).all()
    for parent in parents:
        if parent.primary_phone:
            encrypted, nonce = encryption.encrypt_phone(parent.primary_phone)
            parent._primary_phone_encrypted = encrypted
            parent._primary_phone_nonce = nonce
    
    await db.commit()
    
    # Migrate transcripts
    reports = await db.query(AbsenceReport).all()
    for report in reports:
        if report.transcript:
            encrypted, nonce = encryption.encrypt_text(report.transcript)
            report._transcript_encrypted = encrypted
            report._transcript_nonce = nonce
    
    await db.commit()
```

### Phase 9B: Application Code Changes

1. **Update Models**: Add hybrid properties with encryption
2. **Update Schemas**: Add field serializers for masking
3. **Update Queries**: Use access control checks
4. **Add Audit Logging**: Log all sensitive data access
5. **Test**: Unit tests for encryption/decryption

### Phase 9C: Testing

**Encryption Tests**
- Encrypt/decrypt roundtrip works
- Nonce is unique per field
- Key rotation works
- Invalid keys raise errors

**Access Control Tests**
- Faculty can access their students' parents
- Faculty cannot access other faculty's students
- Parents can only access their children
- Staff cannot access parent PII
- Admin can access everything

**Masking Tests**
- Admin sees full phone numbers
- Faculty sees masked numbers
- Others see nothing

**Retention Tests**
- Old transcripts are deleted
- Deletion request marks data for removal
- Audit logs retained longer than data

---

## Configuration Required

```env
# New encryption key (32 bytes = 256 bits for AES-256)
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
DATA_ENCRYPTION_KEY=<base64-encoded-32-byte-key>

# Data retention (days)
TRANSCRIPT_RETENTION_DAYS=90
CALL_RETENTION_DAYS=30

# Feature flags (for gradual rollout)
ENABLE_ENCRYPTION=true
REQUIRE_ACCESS_CONTROL=true
```

---

## Security Checklist

- ✅ Sensitive fields encrypted with AES-256-GCM
- ✅ Encryption keys in environment, never in code
- ✅ Row-level access control enforced
- ✅ Phone numbers masked in API responses
- ✅ Transcripts only visible to authorized users
- ✅ Data retention policies automated
- ✅ CCPA deletion requests supported
- ✅ Audit logging on sensitive data access
- ✅ No plaintext PII in logs

---

## Performance Impact

| Operation | Current | Encrypted | Impact |
|-----------|---------|-----------|--------|
| Load Parent | 1ms | 6ms | +5ms per phone field |
| Query Parent list | 50ms | 55ms | +5ms (amortized) |
| Update Parent | 2ms | 12ms | +10ms (2 fields) |
| API Response | 100ms | 105ms | +5ms (serialization) |

**Mitigation**:
- Cache decrypted values in session
- Batch queries to reduce impact
- Use database-level read replicas for queries
- Consider async encryption/decryption

---

## Risks & Mitigation

| Risk | Probability | Mitigation |
|---|---|---|
| Performance degradation | High | Batch queries, caching |
| Key rotation complexity | Medium | Automated rotation script |
| Lost encryption key | Low | Key backup in secure vault |
| Backwards compatibility | High | Hybrid property approach |
| Data migration errors | Medium | Test migration script thoroughly |

---

## Related Documents
- SECURITY_HARDENING_PLAN.md (main plan)
- FERPA compliance guidelines
- CCPA privacy requirements
- backend/models/*.py (model definitions)

---

**Last Updated**: 2026-09-14  
**Status**: Ready for Phase 9 implementation
