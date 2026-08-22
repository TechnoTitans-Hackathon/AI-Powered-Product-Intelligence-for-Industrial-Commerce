"""
Seeds initial realistic industrial products from the official UniHack dataset
and common industrial equipment categories.
"""
from sqlalchemy.orm import Session
from backend.db.models import Product
from backend.services.product_service import product_service
from backend.schemas.product import ProductCreate
from backend.services.job_service import job_service
from backend.core.logging import logger

SAMPLE_PRODUCTS_TO_SEED = [
    ProductCreate(
        name='Diablo 1/2"x18" Sanding Belt 6pc',
        sku="DCB518ASTS06G",
        mpn="DCB518ASTS06G",
        brand="Diablo",
        manufacturer="Freud Inc (2435)",
        category="Abrasives & Finishing",
        industry="Industrial Manufacturing",
        description='DCB518ASTS06G Diablo 1/2"x18" - Sanding Belt 6pc. Premium zirconia blend designed for rapid material removal and extended belt life on portable belt sanders.'
    ),
    ProductCreate(
        name="3M 775L Stikit Film Disc P150 Cubitron II",
        sku="3MABR-7100075678",
        mpn="3MABR-7100075678",
        brand="3M",
        manufacturer="Jam Industrial Supply LLC (JAMIN)",
        category="Abrasives & Cutting",
        industry="Industrial Manufacturing",
        description="3M 775L Stikit Film P150 - Cubitron II 50 Disc/Box. Precision Shaped Grain technology cuts faster and lasts twice as long as conventional ceramic abrasives."
    ),
    ProductCreate(
        name='Oliver 15" Benchtop Planer 2.5HP 1Ph 230V',
        sku="10055.201",
        mpn="10055.201",
        brand="Oliver",
        manufacturer="Oliver Machinery Company (OLIMA)",
        category="Woodworking Machinery",
        industry="Industrial Machinery",
        description='10055.201 Oliver 15" Benchtop Planer 2.5HP 1Ph 230V. Heavy-duty cast iron construction with 4-post design and spiral cutterhead for ultra-smooth surface finishing.'
    ),
    ProductCreate(
        name="Rexroth A10VSO Variable Displacement Axial Piston Pump",
        sku="A10VSO45DFR1-31R",
        mpn="A10VSO45DFR1-31R",
        brand="Bosch Rexroth",
        manufacturer="Bosch Rexroth AG",
        category="Hydraulics & Fluid Power",
        industry="Hydraulic Systems",
        description="Rexroth A10VSO45DFR1/31R-PPA12N00 Axial Piston Variable Pump. Nominal pressure 280 bar, Maximum pressure 350 bar. Designed for hydrostatic drives in open circuits."
    ),
    ProductCreate(
        name="SKF Explorer Deep Groove Ball Bearing 6205-2RSH",
        sku="SKF-6205-2RSH",
        mpn="6205-2RSH",
        brand="SKF",
        manufacturer="SKF Group",
        category="Bearings & Power Transmission",
        industry="Mechanical Power Transmission",
        description="SKF Explorer 6205-2RSH Deep Groove Ball Bearing with dual contact rubber seals. Bore 25mm, Outer Diameter 52mm, Width 15mm. Dynamic load rating 14.8 kN."
    )
]


def seed_demo_products_if_empty(db: Session):
    """Seed sample products and run intelligence pipeline only in development mode if products table is empty."""
    import os
    env = os.environ.get("ENVIRONMENT", "development").lower()
    seed_flag = os.environ.get("SEED_DEMO_PRODUCTS", "true" if env == "development" else "false").lower()

    if seed_flag not in ("true", "1", "yes"):
        logger.info("Demo product seeding disabled (Production mode). Starting with clean catalog.")
        return

    count = db.query(Product).count()
    if count > 0:
        logger.info(f"Database already contains {count} products. Skipping demo seed.")
        return

    logger.info("Seeding initial industrial products with multi-agent intelligence (Development mode)...")
    for item in SAMPLE_PRODUCTS_TO_SEED:
        try:
            prod = product_service.create_product(db, item)
            job = job_service.create_job(db, prod.id)
            import asyncio
            asyncio.run(job_service.run_pipeline(db, job.id))
            logger.info(f"Seeded and processed product: {prod.name} ({prod.id})")
        except Exception as e:
            logger.warning(f"Error seeding product {item.name}: {e}")
