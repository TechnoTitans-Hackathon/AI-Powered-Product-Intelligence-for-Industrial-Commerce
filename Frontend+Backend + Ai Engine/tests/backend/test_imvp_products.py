def test_product_crud(client):
    # 1. Create product
    payload = {
        "name": "Deep Groove Ball Bearing 6205-2RS1",
        "sku": "SKF-6205-2RS1",
        "brand": "SKF",
        "category": "Bearings",
        "description": "High performance SKF deep groove ball bearing"
    }
    res = client.post("/api/v1/products", json=payload)
    assert res.status_code == 201
    prod = res.json()
    assert prod["name"] == payload["name"]
    assert prod["sku"] == payload["sku"]
    product_id = prod["id"]

    # 2. Get product
    res_get = client.get(f"/api/v1/products/{product_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == product_id

    # 3. List products
    res_list = client.get("/api/v1/products")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # 4. Update product
    update_payload = {"description": "Updated SKF bearing description"}
    res_upd = client.put(f"/api/v1/products/{product_id}", json=update_payload)
    assert res_upd.status_code == 200
    assert res_upd.json()["description"] == update_payload["description"]
