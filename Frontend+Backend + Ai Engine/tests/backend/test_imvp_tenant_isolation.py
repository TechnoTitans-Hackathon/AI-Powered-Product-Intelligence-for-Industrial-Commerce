import pytest
from fastapi.testclient import TestClient
from backend.db.models import Product, Tenant, User, ProcessingJob, ValidationResult


def test_tenant_registration_and_isolation(client: TestClient):
    # 1. Register Company A
    res_a = client.post("/api/v1/auth/register", json={
        "name": "Alice Admin",
        "email": "alice@companya.com",
        "company_name": "Company A Industrial",
        "industry": "Pneumatics"
    })
    assert res_a.status_code == 201
    data_a = res_a.json()
    tenant_a_id = data_a["tenant"]["id"]
    token_a = data_a["access_token"]
    headers_a = {"X-Tenant-ID": tenant_a_id, "Authorization": f"Bearer {token_a}"}

    # 2. Verify Company A starts with 0 products and 0 jobs in analytics
    analytics_a = client.get("/api/v1/analytics/summary", headers=headers_a)
    assert analytics_a.status_code == 200
    assert analytics_a.json()["products"]["total"] == 0
    assert analytics_a.json()["jobs"]["total"] == 0

    # 3. Create a product in Company A
    prod_a_res = client.post("/api/v1/products", json={
        "name": "Company A Pneumatic Cylinder 50mm",
        "sku": "CYL-A-50",
        "brand": "Company A Pneumatics",
        "category": "Pneumatics",
        "description": "50mm bore double acting cylinder"
    }, params={"auto_process": False}, headers=headers_a)
    assert prod_a_res.status_code == 201
    prod_a_id = prod_a_res.json()["id"]

    # Verify Company A catalog now has 1 product
    cat_a = client.get("/api/v1/products", headers=headers_a)
    assert cat_a.status_code == 200
    assert len(cat_a.json()) == 1
    assert cat_a.json()[0]["id"] == prod_a_id

    # 4. Register Company B
    res_b = client.post("/api/v1/auth/register", json={
        "name": "Bob Admin",
        "email": "bob@companyb.com",
        "company_name": "Company B Hydraulics",
        "industry": "Hydraulics"
    })
    assert res_b.status_code == 201
    data_b = res_b.json()
    tenant_b_id = data_b["tenant"]["id"]
    token_b = data_b["access_token"]
    headers_b = {"X-Tenant-ID": tenant_b_id, "Authorization": f"Bearer {token_b}"}

    # 5. Verify Company B starts with 0 products in catalog and analytics
    cat_b = client.get("/api/v1/products", headers=headers_b)
    assert cat_b.status_code == 200
    assert len(cat_b.json()) == 0

    analytics_b = client.get("/api/v1/analytics/summary", headers=headers_b)
    assert analytics_b.status_code == 200
    assert analytics_b.json()["products"]["total"] == 0

    # 6. Verify Company B CANNOT access Company A's product by ID (must return 404)
    cross_tenant_get = client.get(f"/api/v1/products/{prod_a_id}", headers=headers_b)
    assert cross_tenant_get.status_code == 404

    cross_tenant_intel = client.get(f"/api/v1/products/{prod_a_id}/intelligence", headers=headers_b)
    assert cross_tenant_intel.status_code == 404

    cross_tenant_explain = client.get(f"/api/v1/explainability/{prod_a_id}", headers=headers_b)
    assert cross_tenant_explain.status_code == 404

    # 7. Create a product in Company B
    prod_b_res = client.post("/api/v1/products", json={
        "name": "Company B Hydraulic Pump 250Bar",
        "sku": "PUMP-B-250",
        "brand": "Company B Hydraulics",
        "category": "Hydraulics",
        "description": "High pressure axial piston pump"
    }, params={"auto_process": False}, headers=headers_b)
    assert prod_b_res.status_code == 201
    prod_b_id = prod_b_res.json()["id"]

    # Verify Company B has 1 product and Company A has 1 product
    assert len(client.get("/api/v1/products", headers=headers_a).json()) == 1
    assert len(client.get("/api/v1/products", headers=headers_b).json()) == 1
    assert client.get("/api/v1/products", headers=headers_a).json()[0]["id"] == prod_a_id
    assert client.get("/api/v1/products", headers=headers_b).json()[0]["id"] == prod_b_id

    # 8. Verify cross-tenant isolation on delete and update
    cross_delete = client.delete(f"/api/v1/products/{prod_a_id}", headers=headers_b)
    assert cross_delete.status_code == 404

    cross_update = client.put(f"/api/v1/products/{prod_a_id}", json={"name": "Hacked"}, headers=headers_b)
    assert cross_update.status_code == 404
