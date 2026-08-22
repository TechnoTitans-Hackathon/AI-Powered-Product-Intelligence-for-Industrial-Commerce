from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings, ensure_directories
from backend.core.db import engine, Base, SessionLocal
from backend.db.migrations import run_migrations
from backend.db.seeds.official_seeds import seed_official_knowledge
from backend.db.seeds.demo_products import seed_demo_products_if_empty
from backend.knowledge.baseline_knowledge import initialize_baseline_knowledge
from backend.api.v1.router import api_router
from backend.core.logging import logger

def create_app() -> FastAPI:
    ensure_directories()

    # Create DB tables if missing
    Base.metadata.create_all(bind=engine)

    # Apply migrations, seed official controlled knowledge & baseline corpus
    db = SessionLocal()
    try:
        run_migrations(db)
        seed_official_knowledge(db)
        # Initialize permanent baseline knowledge corpus
        baseline_result = initialize_baseline_knowledge(db)
        logger.info(f"Baseline knowledge status: {baseline_result}")
        # Seed initial products with multi-agent intelligence if DB is fresh
        seed_demo_products_if_empty(db)
    except Exception as e:
        logger.warning(f"Seeding warning: {e}")
    finally:
        db.close()


    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        version="1.0.0"
    )

    # Configure CORS middleware for React frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.API_V1_STR)

    logger.info("Product Intelligence Platform API initialized successfully.")
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
