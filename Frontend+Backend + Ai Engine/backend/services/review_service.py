from sqlalchemy.orm import Session
from typing import Optional
from backend.db.models import Product, HumanReview, Attribute
from backend.schemas.review import HumanReviewRequest, HumanReviewResponse
from backend.core.logging import logger

class ReviewService:
    """
    Handles human review lifecycle and edit audit tracking.
    Never silently overwrites values; records complete change history.
    """

    def submit_review(self, db: Session, product_id: str, payload: HumanReviewRequest) -> HumanReviewResponse:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError(f"Product {product_id} not found.")

        # Record human review entry
        review = HumanReview(
            product_id=product_id,
            reviewer=payload.reviewer,
            action=payload.action,
            comment=payload.comment,
            field_name=payload.field_name,
            previous_value=payload.previous_value,
            new_value=payload.new_value
        )
        db.add(review)

        # Update product review state
        product.review_status = payload.action

        if payload.action == "APPROVED":
            product.status = "verified"
        elif payload.action == "REJECTED":
            product.status = "needs_review"
        elif payload.action == "EDITED" and payload.field_name and payload.new_value:
            # Update specific attribute if key matches
            attr = db.query(Attribute).filter(
                Attribute.product_id == product_id,
                Attribute.key == payload.field_name
            ).first()
            if attr:
                attr.value = payload.new_value
                attr.normalized_value = payload.new_value
                attr.status = "verified"
            else:
                # Add new attribute override
                db_attr = Attribute(
                    product_id=product_id,
                    attribute_type="technical_spec",
                    key=payload.field_name,
                    value=payload.new_value,
                    normalized_value=payload.new_value,
                    confidence=100.0,
                    status="verified",
                    explanation=f"Human override by {payload.reviewer}"
                )
                db.add(db_attr)
            product.status = "verified"

        db.commit()
        db.refresh(review)
        logger.info(f"Recorded human review {review.id} for product {product_id}: Action={payload.action} by {payload.reviewer}")

        return HumanReviewResponse(
            review_id=review.id,
            product_id=review.product_id,
            reviewer=review.reviewer,
            action=review.action,
            comment=review.comment,
            field_name=review.field_name,
            previous_value=review.previous_value,
            new_value=review.new_value,
            created_at=review.created_at.isoformat()
        )

review_service = ReviewService()
