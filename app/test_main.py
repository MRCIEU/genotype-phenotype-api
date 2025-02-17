import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app, get_db
from app.database import Base, engine, SessionLocal


SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_create_item():
    response = client.post(
        "/items/",
        json={"name": "Test Item", "description": "This is a test item"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Item"
    assert data["description"] == "This is a test item"
    assert "id" in data

def test_read_item():
    response = client.post(
        "/items/",
        json={"name": "Test Item", "description": "This is a test item"},
    )
    item_id = response.json()["id"]

    response = client.get(f"/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Item"
    assert data["description"] == "This is a test item"
    assert data["id"] == item_id

def test_read_items():
    response = client.get("/items/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_update_item():
    response = client.post(
        "/items/",
        json={"name": "Test Item", "description": "This is a test item"},
    )
    item_id = response.json()["id"]

    response = client.put(
        f"/items/{item_id}",
        json={"name": "Updated Test Item", "description": "This is an updated test item"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Test Item"
    assert data["description"] == "This is an updated test item"
    assert data["id"] == item_id

def test_delete_item():
    response = client.post(
        "/items/",
        json={"name": "Test Item", "description": "This is a test item"},
    )
    item_id = response.json()["id"]

    response = client.delete(f"/items/{item_id}")
    assert response.status_code == 200

    response = client.get(f"/items/{item_id}")
    assert response.status_code == 404