import io
from pathlib import Path
import pytest
import numpy as np
import cv2
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db

# Use an in-memory SQLite database for test isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def sharp_image_bytes():
    """Generates a sharp 320x240 JPEG with high edge variance."""
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    img[:, :] = (210, 210, 210)
    cv2.circle(img, (160, 120), 40, (20, 20, 20), -1)
    cv2.putText(img, "Test", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()

@pytest.fixture
def blurry_image_bytes():
    """Generates a flat uniform 320x240 JPEG with zero edge variance."""
    img = np.ones((240, 320, 3), dtype=np.uint8) * 128
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()
