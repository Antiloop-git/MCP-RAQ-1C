import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from embedding_service import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True


def test_model_info(client):
    resp = client.get("/model-info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["dimensions"] == 768
    assert "BERTA" in data["model"]


def test_dense_embedding(client):
    resp = client.post("/embed", json={
        "texts": ["Справочник: Номенклатура", "Документ: Заказ клиента"],
        "prefix": "search_document",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["dimensions"] == 768
    assert data["count"] == 2
    assert len(data["embeddings"]) == 2
    assert len(data["embeddings"][0]) == 768


def test_dense_russian_text(client):
    resp = client.post("/embed", json={
        "texts": ["Регистр накопления: Остатки товаров"],
        "prefix": "search_query",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert len(data["embeddings"][0]) == 768


def test_dense_batch_32(client):
    texts = [f"Объект метаданных {i}" for i in range(32)]
    resp = client.post("/embed", json={
        "texts": texts,
        "prefix": "search_document",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 32


def test_sparse_embedding(client):
    resp = client.post("/embed-sparse", json={
        "texts": ["Справочник: Номенклатура"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    emb = data["embeddings"][0]
    assert len(emb["indices"]) > 0
    assert len(emb["values"]) > 0
    assert len(emb["indices"]) == len(emb["values"])


def test_validation_empty_texts(client):
    resp = client.post("/embed", json={
        "texts": [],
        "prefix": "search_document",
    })
    assert resp.status_code == 422


def test_validation_too_many_texts(client):
    texts = [f"text {i}" for i in range(33)]
    resp = client.post("/embed", json={
        "texts": texts,
        "prefix": "search_document",
    })
    assert resp.status_code == 422


def test_validation_invalid_prefix(client):
    resp = client.post("/embed", json={
        "texts": ["test"],
        "prefix": "invalid",
    })
    assert resp.status_code == 422


def test_validation_sparse_empty_texts(client):
    resp = client.post("/embed-sparse", json={"texts": []})
    assert resp.status_code == 422


def test_validation_sparse_too_many_texts(client):
    texts = [f"text {i}" for i in range(33)]
    resp = client.post("/embed-sparse", json={"texts": texts})
    assert resp.status_code == 422
