"""Auth & Multi-Tenant Management API endpoints."""
import uuid
import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.core.db import get_db
from backend.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_tenant,
    get_current_user,
)
from backend.db.models import Tenant, User, Product, ProcessingJob, ValidationResult
from backend.core.logging import logger

router = APIRouter()


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-') or f"tenant-{uuid.uuid4().hex[:6]}"


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: Optional[str] = "password123"
    company_name: str
    industry: Optional[str] = "Industrial Manufacturing"


class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = "password123"



class SwitchTenantRequest(BaseModel):
    tenant_id: str


@router.post("/auth/register", response_model=Dict[str, Any], status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user and create an isolated company tenant."""
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    # Generate unique tenant slug & ID
    base_slug = slugify(payload.company_name)
    slug = base_slug
    idx = 1
    while db.query(Tenant).filter(Tenant.slug == slug).first():
        slug = f"{base_slug}-{idx}"
        idx += 1

    tenant = Tenant(
        id=f"tenant_{uuid.uuid4().hex[:10]}",
        name=payload.company_name.strip(),
        slug=slug,
        industry=payload.industry or "Industrial Manufacturing",
        plan="enterprise",
        is_active=True,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    user = User(
        id=f"user_{uuid.uuid4().hex[:10]}",
        tenant_id=tenant.id,
        email=payload.email.lower().strip(),
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, tenant_id=tenant.id, role=user.role)
    logger.info(f"Registered new company tenant: {tenant.name} ({tenant.id}), User: {user.email}")

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "industry": tenant.industry,
        },
        "message": f"Successfully created {tenant.name}. Fresh isolated workspace initialized."
    }


@router.post("/auth/login", response_model=Dict[str, Any])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate existing user and return tenant context."""
    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    # Fallback initialization for prototype demo credentials if not yet seeded
    if not user and email == "employee@demo.com" and payload.password == "demo123":
        demo_tenant = db.query(Tenant).filter(Tenant.id == "demo").first()
        if not demo_tenant:
            demo_tenant = Tenant(
                id="demo",
                name="Demo Industrial Catalog",
                slug="demo",
                industry="Industrial Machinery & Components",
                plan="enterprise",
                is_active=True,
            )
            db.add(demo_tenant)
            db.commit()

        user = User(
            id="user_employee_demo",
            tenant_id="demo",
            email="employee@demo.com",
            name="Demo Employee",
            password_hash=hash_password("demo123"),
            role="specialist",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant:
        tenant = db.query(Tenant).filter(Tenant.id == "demo").first()

    token = create_access_token(user_id=user.id, tenant_id=tenant.id if tenant else "demo", role=user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
        "tenant": {
            "id": tenant.id if tenant else "demo",
            "name": tenant.name if tenant else "Demo Industrial Catalog",
            "slug": tenant.slug if tenant else "demo",
            "industry": tenant.industry if tenant else "Industrial",
        } if tenant else None,
    }



@router.get("/auth/me", response_model=Dict[str, Any])
def get_me(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
    user: Optional[User] = Depends(get_current_user),
):
    """Return active user profile and current tenant workspace details."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant and tenant_id == "demo":
        tenant = Tenant(
            id="demo",
            name="Demo Industrial Catalog",
            slug="demo",
            industry="Industrial Manufacturing",
            plan="enterprise",
        )

    # Compute quick tenant stats
    prod_count = db.query(Product).filter(Product.tenant_id == tenant_id).count()

    return {
        "user": {
            "id": user.id if user else "user_specialist",
            "name": user.name if user else "Product Specialist",
            "email": user.email if user else "specialist@industrial.ai",
            "role": user.role if user else "specialist",
        },
        "tenant": {
            "id": tenant.id if tenant else tenant_id,
            "name": tenant.name if tenant else "Current Workspace",
            "slug": tenant.slug if tenant else tenant_id,
            "industry": tenant.industry if tenant else "Industrial",
            "total_products": prod_count,
        } if tenant else {
            "id": tenant_id,
            "name": "Active Workspace",
            "slug": tenant_id,
            "total_products": prod_count,
        }
    }


@router.get("/auth/tenants", response_model=List[Dict[str, Any]])
def list_tenants(db: Session = Depends(get_db)):
    """List available tenant workspaces for easy switching/onboarding."""
    tenants = db.query(Tenant).filter(Tenant.is_active == True).order_by(Tenant.created_at.desc()).all()
    results = []
    
    # Ensure demo is present
    has_demo = False
    for t in tenants:
        if t.id == "demo":
            has_demo = True
        prod_count = db.query(Product).filter(Product.tenant_id == t.id).count()
        results.append({
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "industry": t.industry,
            "product_count": prod_count,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })

    if not has_demo:
        demo_prod_count = db.query(Product).filter(Product.tenant_id == "demo").count()
        results.insert(0, {
            "id": "demo",
            "name": "Demo Industrial Catalog",
            "slug": "demo",
            "industry": "Industrial Manufacturing",
            "product_count": demo_prod_count,
            "created_at": None,
        })

    return results


@router.post("/auth/switch-tenant", response_model=Dict[str, Any])
def switch_tenant(payload: SwitchTenantRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_current_user)):
    """Switch active tenant workspace."""
    tenant = db.query(Tenant).filter(Tenant.id == payload.tenant_id).first()
    if not tenant and payload.tenant_id != "demo":
        raise HTTPException(status_code=404, detail=f"Tenant {payload.tenant_id} not found.")

    token = create_access_token(
        user_id=user.id if user else "user_demo",
        tenant_id=payload.tenant_id,
        role=user.role if user else "specialist"
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "tenant": {
            "id": tenant.id if tenant else payload.tenant_id,
            "name": tenant.name if tenant else "Demo Industrial Catalog",
            "slug": tenant.slug if tenant else payload.tenant_id,
            "industry": tenant.industry if tenant else "Industrial",
        }
    }
