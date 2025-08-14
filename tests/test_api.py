import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import os

from main import app
from app.models.database import Base, get_db

# Create test database
@pytest.fixture
def test_db():
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()
    database_url = f"sqlite:///{db_path}"
    
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield TestingSessionLocal
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(test_db):
    return TestClient(app)

def test_create_payment(client):
    """Test payment creation"""
    payment_data = {
        "merchant_id": "MERCH_001",
        "customer_id": "CUST_001",
        "amount": 1000.0,
        "currency": "SZL",
        "payment_method": "qr_code",
        "customer_location": "Manzini"
    }
    
    response = client.post("/api/v1/payments", json=payment_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "payment_id" in data
    assert data["status"] == "pending"
    assert data["message"] == "Payment initiated successfully"

def test_invalid_merchant(client):
    """Test invalid merchant ID"""
    payment_data = {
        "merchant_id": "INVALID_001",
        "customer_id": "CUST_001",
        "amount": 1000.0,
        "currency": "SZL",
        "payment_method": "qr_code"
    }
    
    response = client.post("/api/v1/payments", json=payment_data)
    assert response.status_code == 401
    assert "Invalid merchant credentials" in response.json()["detail"]

def test_get_payment_status(client):
    """Test getting payment status"""
    # First create a payment
    payment_data = {
        "merchant_id": "MERCH_001",
        "customer_id": "CUST_001",
        "amount": 500.0,
        "currency": "SZL",
        "payment_method": "qr_code"
    }
    
    create_response = client.post("/api/v1/payments", json=payment_data)
    payment_id = create_response.json()["payment_id"]
    
    # Get payment status
    response = client.get(f"/api/v1/payments/{payment_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["payment_id"] == payment_id
    assert data["amount"] == 500.0
    assert data["currency"] == "SZL"

def test_analytics_dashboard(client):
    """Test analytics endpoint"""
    response = client.get("/api/v1/analytics/dashboard")
    assert response.status_code == 200
    
    data = response.json()
    assert "summary" in data
    assert "settlement_distribution" in data
    assert "risk_distribution" in data

def test_demo_frontend(client):
    """Test frontend endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "Eswatini Payment System Demo" in response.text