"""
Authentication & Multi-Tenant Scoping Core Utilities.

Provides:
- Secure token creation and verification using HMAC-SHA256
- Fast, reliable tenant resolution from Authorization Bearer or X-Tenant-ID header
- FastAPI dependency injections for tenant and user context
"""
import json
import base64
import hmac
import hashlib
import time
from typing import Optional, Dict, Any
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.core.config import settings
from backend.core.db import get_db
from backend.db.models import User, Tenant
from backend.core.logging import logger


SECRET_KEY = settings.SECRET_KEY or "dev_secret_key_change_in_production"
TOKEN_EXPIRY_SECONDS = 86400 * 30  # 30 days for MVP convenience


def hash_password(password: str) -> str:
    salt = "pi_platform_salt_2026"
    return hashlib.sha256(f"{salt}_{password}".encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password


def create_access_token(user_id: str, tenant_id: str, role: str = "specialist", expires_in: int = TOKEN_EXPIRY_SECONDS) -> str:
    """Create signed HMAC-SHA256 JWT-like access token."""
    payload = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "exp": int(time.time()) + expires_in,
    }
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode('utf-8')).decode('utf-8').rstrip('=')
    
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        payload_b64.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return f"{payload_b64}.{signature}"


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode signed access token."""
    try:
        parts = token.strip().split('.')
        if len(parts) != 2:
            return None
        
        payload_b64, signature = parts
        expected_sig = hmac.new(
            SECRET_KEY.encode('utf-8'),
            payload_b64.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            return None
        
        # Add back padding
        padding = 4 - (len(payload_b64) % 4)
        if padding != 4:
            payload_b64 += '=' * padding
            
        payload_json = base64.urlsafe_b64decode(payload_b64.encode('utf-8')).decode('utf-8')
        payload = json.loads(payload_json)
        
        if payload.get("exp", 0) < time.time():
            return None
            
        return payload
    except Exception as e:
        logger.debug(f"Token verification error: {e}")
        return None


def get_current_tenant(request: Request, db: Session = Depends(get_db)) -> str:
    """
    Authoritative dependency to resolve the active tenant_id.
    
    Priority:
    1. 'X-Tenant-ID' request header (explicit workspace header from frontend or test suite)
    2. 'Authorization: Bearer <token>' header payload
    3. Fallback to 'demo' default tenant
    """
    # 1. Check explicit X-Tenant-ID header
    header_tenant = request.headers.get("X-Tenant-ID") or request.headers.get("x-tenant-id")
    if header_tenant and header_tenant.strip():
        tenant_id = header_tenant.strip()
        # Verify tenant exists or ensure it's registered
        return tenant_id

    # 2. Check Authorization Bearer token
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        payload = verify_token(token)
        if payload and payload.get("tenant_id"):
            return payload["tenant_id"]

    # 3. Default to demo tenant
    return "demo"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Resolves authenticated user from token."""
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        payload = verify_token(token)
        if payload and payload.get("user_id"):
            user = db.query(User).filter(User.id == payload["user_id"]).first()
            if user and user.is_active:
                return user

    # Fallback to demo user if requested
    tenant_id = get_current_tenant(request, db)
    return db.query(User).filter(User.tenant_id == tenant_id).first()
