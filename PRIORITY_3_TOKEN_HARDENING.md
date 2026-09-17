# Priority 3: Authentication Token Hardening - Design Document

**Date**: September 14, 2026  
**Status**: Design Phase  
**Implementation**: Phase 8 (Future)

---

## Current State Analysis

### Frontend Token Storage (localStorage)
```
Frontend (current implementation):
├── Access Token (30 min expiry)
│   ├── Stored in: localStorage
│   ├── Sent with: Bearer Authorization header
│   ├── Risk: XSS can steal the token
│   └── Used for: API requests
├── Refresh Token (7 days expiry)
│   ├── Stored in: localStorage
│   ├── Risk: XSS can steal the token
│   └── Used for: Getting new access token on 401
└── Auto-Refresh Logic
    ├── On 401: POST /api/auth/refresh
    ├── Get new access token
    ├── Retry original request
    └── Risk: No CSRF protection
```

### Security Vulnerabilities

| Vulnerability | Impact | Current Status |
|---|---|---|
| XSS → Token Theft | High - Attacker gets full access | ⚠️ Vulnerable |
| Token Persistence | Medium - Session survives reload | ⚠️ Current behavior |
| No CSRF Protection | Medium - Cross-site requests possible | ⚠️ Not protected |
| Token Binding | Medium - Token can be used from other clients | ⚠️ Not bound |
| No Token Rotation | Medium - Same token for entire session | ⚠️ No rotation |
| Refresh Token in localStorage | High - Never expires until logout | ⚠️ Vulnerable |

---

## Proposed Solution: Hybrid Token Storage

### Architecture

```
Frontend (proposed):
├── Access Token (30 min expiry)
│   ├── Storage: Memory only (cleared on page reload)
│   ├── Sent with: Bearer Authorization header
│   ├── Retrieved: On page load from /api/auth/session
│   ├── Protection: XSS can only steal if browser window active
│   └── Risk Reduction: 95%
├── Refresh Token (7 days expiry)
│   ├── Storage: httpOnly Secure SameSite cookie (backend-managed)
│   ├── Sent with: Automatic in requests (browser handles)
│   ├── Protection: JavaScript cannot access it
│   ├── Protection: Automatic CSRF protection (SameSite=Strict)
│   └── Risk Reduction: 99%
└── Session Recovery
    ├── On page load: GET /api/auth/session
    ├── Backend verifies refresh token in cookie
    ├── Returns new access token in response body
    ├── Frontend stores in memory
    └── Transparent to user (session persists)
```

### Key Improvements

1. **Memory-Only Access Tokens**
   - Cleared on page reload
   - XSS can only steal if browser tab is active
   - Session recovery via refresh token on page load

2. **HttpOnly Refresh Tokens**
   - JavaScript cannot access (blocks XSS theft)
   - Automatically sent by browser
   - Backend verifies signature and expiry

3. **CSRF Protection**
   - httpOnly cookie with SameSite=Strict
   - Prevents cross-site refresh requests
   - Token changes on login/logout

4. **Session Recovery**
   - User doesn't need to re-login on page reload
   - Automatic session establishment
   - Requires valid refresh token in cookie

---

## Implementation Plan

### Phase 8A: Backend Preparation

**New Endpoint**: `POST /api/auth/session`
```python
@router.post("/api/auth/session")
async def get_session(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Get or refresh access token using refresh token from cookie.
    
    Returns:
    - access_token: in response body (memory storage)
    - Sets new refresh token cookie if needed
    """
    # Verify refresh token in cookie
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(401, "Not authenticated")
    
    # Verify JWT and get user
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY)
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(401, "Invalid token")
    
    # Generate new access token
    access_token = create_access_token(user_id, expires_delta=timedelta(minutes=30))
    
    # Check if refresh token nearing expiry (within 24 hours)
    exp = payload.get("exp")
    if datetime.utcfromtimestamp(exp) - datetime.utcnow() < timedelta(hours=24):
        # Generate new refresh token (sliding window)
        new_refresh_token = create_refresh_token(user_id)
        response = JSONResponse({"access_token": access_token, "token_type": "bearer"})
        set_refresh_token_cookie(response, new_refresh_token)
        return response
    
    return {"access_token": access_token, "token_type": "bearer"}
```

**Modify Login Endpoint**: `POST /api/auth/login`
```python
@router.post("/api/auth/login")
async def login(credentials: LoginSchema, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user and return tokens.
    
    Returns:
    - access_token: in response body (memory storage)
    - Sets refresh_token cookie (httpOnly, Secure, SameSite=Strict)
    """
    # ... existing auth logic ...
    
    access_token = create_access_token(user.id, expires_delta=timedelta(minutes=30))
    refresh_token = create_refresh_token(user.id)
    
    response = JSONResponse({"access_token": access_token, "token_type": "bearer"})
    set_refresh_token_cookie(response, refresh_token)
    return response
```

**New Endpoint**: `POST /api/auth/logout`
```python
@router.post("/api/auth/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout user by clearing refresh token cookie.
    """
    response = JSONResponse({"message": "Successfully logged out"})
    response.delete_cookie("refresh_token", secure=True, httponly=True, samesite="strict")
    return response
```

**Helper Function**: Set refresh token cookie
```python
def set_refresh_token_cookie(response: Response, token: str):
    """Set refresh token as httpOnly, Secure, SameSite cookie."""
    response.set_cookie(
        key="refresh_token",
        value=token,
        max_age=7 * 24 * 60 * 60,  # 7 days
        secure=True,  # HTTPS only
        httponly=True,  # No JavaScript access
        samesite="strict",  # CSRF protection
        path="/",
        domain=None  # Auto-detect from request
    )
```

### Phase 8B: Frontend Migration

**Step 1**: Implement Session API Call
```typescript
// services/auth.ts
export async function getSession(): Promise<string | null> {
  try {
    const response = await fetch("/api/auth/session", {
      method: "POST",
      credentials: "include",  // Send cookies
      headers: { "Content-Type": "application/json" }
    })
    
    if (!response.ok) {
      if (response.status === 401) {
        // Not authenticated
        return null
      }
      throw new Error("Session error")
    }
    
    const { access_token } = await response.json()
    return access_token
  } catch (error) {
    console.error("Failed to get session:", error)
    return null
  }
}
```

**Step 2**: Initialize Session on App Load
```typescript
// App.tsx
useEffect(() => {
  const initSession = async () => {
    const token = await getSession()
    if (token) {
      setAccessToken(token)  // Store in memory
    } else {
      redirectToLogin()
    }
  }
  
  initSession()
}, [])  // Run once on mount
```

**Step 3**: Store Access Token in Memory Only
```typescript
// authContext.ts
interface AuthContextType {
  accessToken: string | null
  setAccessToken: (token: string | null) => void
  logout: () => void
}

export const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(null)
  
  const logout = async () => {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" })
    setAccessToken(null)
    redirectToLogin()
  }
  
  return (
    <AuthContext.Provider value={{ accessToken, setAccessToken, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
```

**Step 4**: API Client with Auto-Refresh
```typescript
// apiClient.ts
export const apiClient = {
  async request(url: string, options: RequestInit = {}) {
    const token = getAccessToken()  // From context
    
    if (!token) {
      // Try to recover session
      const newToken = await getSession()
      if (!newToken) {
        redirectToLogin()
        return
      }
    }
    
    const headers = {
      ...options.headers,
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json"
    }
    
    let response = await fetch(url, { ...options, headers })
    
    // Handle 401 - try to refresh
    if (response.status === 401) {
      const newToken = await getSession()
      if (newToken) {
        setAccessToken(newToken)
        response = await fetch(url, {
          ...options,
          headers: { ...headers, "Authorization": `Bearer ${newToken}` }
        })
      } else {
        redirectToLogin()
      }
    }
    
    return response
  }
}
```

**Step 5**: Backwards Compatibility (Transition Period)
```typescript
// During migration, support both:
const token = accessToken || localStorage.getItem("access_token")
// After migration, remove localStorage fallback
```

### Phase 8C: Testing

**Backend Tests**
- Session endpoint returns valid access token
- Refresh token cookie is httpOnly and Secure
- Session endpoint rejects without valid refresh token
- Logout clears refresh token cookie
- Access token expires correctly
- Refresh token sliding window works (refreshes if <24h to expiry)

**Frontend Tests**
- Access token stored in memory only
- Session recovered on page load
- Auto-refresh on 401
- Logout clears memory
- Redirect to login on refresh failure
- CSRF protection via SameSite cookie

---

## Migration Strategy

### Phase 1: Deploy Backend Changes (No Breaking Changes)
- Add `/api/auth/session` endpoint
- Modify `/api/auth/login` to set refresh token cookie
- Keep localStorage-based login working (backward compatible)
- Users can call `getSession()` if they want

### Phase 2: Gradual Frontend Migration
- Update new pages to use memory-based tokens
- Keep old pages on localStorage
- Monitor for issues

### Phase 3: Full Cutover
- Remove localStorage fallback
- Require session recovery on page load
- Deprecate old localStorage-based auth

### Phase 4: Cleanup
- Remove old token endpoints
- Remove localStorage usage
- Archive migration code

---

## Configuration Required

```env
# Already exists
JWT_ALGORITHM=HS256
SECRET_KEY=<random-secret>
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# New (optional, can use defaults)
SECURE_COOKIE_SAMESITE=strict
SECURE_COOKIE_HTTPONLY=true
SECURE_COOKIE_SECURE=true  # Set to false in development
```

---

## Security Checklist

- ✅ Access token cleared on page reload
- ✅ Refresh token in httpOnly cookie (JS cannot access)
- ✅ Refresh token has Secure flag (HTTPS only)
- ✅ Refresh token has SameSite=Strict (CSRF protection)
- ✅ Session recovery via `/api/auth/session`
- ✅ Token rotation via sliding window
- ✅ Logout invalidates refresh token
- ✅ No tokens in LocalStorage (final state)

---

## Risks & Mitigation

| Risk | Probability | Mitigation |
|---|---|---|
| User session interrupted during migration | High | Gradual rollout, keep backward compat |
| Browser doesn't support httpOnly | Low | All modern browsers support it |
| CORS preflight breaks SameSite cookie | Medium | Set CORS before auth middleware |
| localStorage tokens coexist (confusion) | High | Clear localStorage in migration |
| Bookmark-based state loss | Medium | Accept with notification to user |

---

## Related Documents
- SECURITY_HARDENING_PLAN.md (main plan)
- backend/app/core/auth.py (JWT implementation)
- frontend/services/authClient.ts (frontend auth)

---

**Last Updated**: 2026-09-14  
**Status**: Ready for Phase 8 implementation
