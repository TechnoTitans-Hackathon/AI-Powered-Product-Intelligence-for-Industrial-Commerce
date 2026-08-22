"""
Database Migration & Tenant Schema Initialization.

Ensures that:
1. 'tenant_id' column is added to all relevant tables if missing (SQLite compatible).
2. Existing 10,005 products and related records remain intact under 'tenant_id' = 'demo'.
3. 'tenants' and 'users' tables are created and seeded with default tenants.
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.db.models import Tenant, User
from backend.core.logging import logger
import hashlib
import uuid


def hash_password(password: str) -> str:
    """Deterministic salted SHA256 password hash."""
    salt = "pi_platform_salt_2026"
    return hashlib.sha256(f"{salt}_{password}".encode("utf-8")).hexdigest()


def run_migrations(db: Session):
    """Safely apply schema additions and baseline tenants without data loss."""
    tables_to_check = [
        "products",
        "attributes",
        "source_documents",
        "evidences",
        "processing_jobs",
        "validation_results",
        "human_reviews",
    ]

    for table in tables_to_check:
        try:
            # Check existing columns using SQLite PRAGMA
            result = db.execute(text(f"PRAGMA table_info({table});")).fetchall()
            col_names = [row[1] for row in result]
            if "tenant_id" not in col_names and len(col_names) > 0:
                logger.info(f"Adding 'tenant_id' column to existing table '{table}'...")
                db.execute(text(f"ALTER TABLE {table} ADD COLUMN tenant_id TEXT DEFAULT 'demo';"))
                db.execute(text(f"UPDATE {table} SET tenant_id = 'demo' WHERE tenant_id IS NULL OR tenant_id = '';"))
                db.commit()
        except Exception as e:
            logger.warning(f"Migration check for table {table}: {e}")
            db.rollback()

    # Add ai_mode to processing_jobs if missing
    try:
        result = db.execute(text("PRAGMA table_info(processing_jobs);")).fetchall()
        col_names = [row[1] for row in result]
        if "ai_mode" not in col_names and len(col_names) > 0:
            logger.info("Adding 'ai_mode' column to existing table 'processing_jobs'...")
            db.execute(text("ALTER TABLE processing_jobs ADD COLUMN ai_mode TEXT DEFAULT 'AUTO';"))
            db.commit()
    except Exception as e:
        logger.warning(f"Migration check for ai_mode on processing_jobs: {e}")
        db.rollback()

    # Create ai_trace_logs if missing
    try:
        result = db.execute(text("PRAGMA table_info(ai_trace_logs);")).fetchall()
        if not result:
            logger.info("Creating 'ai_trace_logs' table...")
            from backend.core.db import Base, engine
            # Only create this specific table to avoid interfering with others
            from backend.db.models import AITraceLog
            AITraceLog.__table__.create(bind=engine, checkfirst=True)
            db.commit()
    except Exception as e:
        logger.warning(f"Migration check for ai_trace_logs: {e}")
        db.rollback()

    # Ensure baseline Demo tenant exists
    try:
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
            db.refresh(demo_tenant)
            logger.info("Initialized default 'demo' tenant.")

        # Ensure prototype employee user exists (employee@demo.com / demo123)
        employee_user = db.query(User).filter(User.email == "employee@demo.com").first()
        if not employee_user:
            employee_user = User(
                id="user_employee_demo",
                tenant_id="demo",
                email="employee@demo.com",
                name="Demo Employee",
                password_hash=hash_password("demo123"),
                role="specialist",
                is_active=True,
            )
            db.add(employee_user)
            db.commit()
            logger.info("Initialized default prototype employee user (employee@demo.com).")
        else:
            # Update password hash if needed
            employee_user.password_hash = hash_password("demo123")
            employee_user.tenant_id = "demo"
            db.commit()

        # Also ensure demo@productai.com exists for backward compatibility
        demo_user = db.query(User).filter(User.email == "demo@productai.com").first()
        if not demo_user:
            demo_user = User(
                id="user_demo_001",
                tenant_id="demo",
                email="demo@productai.com",
                name="Demo Specialist",
                password_hash=hash_password("demo123"),
                role="admin",
                is_active=True,
            )
            db.add(demo_user)
            db.commit()
            logger.info("Initialized default demo user.")
    except Exception as e:
        logger.warning(f"Error seeding demo tenant: {e}")
        db.rollback()

