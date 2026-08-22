from backend.db.models import Product, Attribute
from backend.services.validation_service import validation_service

def test_validation_engine(db_session):
    product = Product(
        name="Deep Groove Ball Bearing 6205-2RS1",
        sku="SKF-6205-2RS1",
        brand="SKF",
        manufacturer="SKF Group",
        category="Bearings"
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    attr = Attribute(
        product_id=product.id,
        key="Bore",
        value="25 mm",
        unit="mm",
        status="verified"
    )
    db_session.add(attr)
    db_session.commit()

    val_res = validation_service.validate_product(db_session, product)
    assert val_res.status == "PASS"
    assert val_res.score >= 90.0
    assert len(val_res.errors) == 0
