"""Test configuration, fixtures, and isolated environments for CreditMera test suite.
"""
import io
import shutil
import tempfile
from pathlib import Path
from typing import Generator
import pytest
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.config import get_settings
from app.core.security import hash_password, create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.models.asset import RegisteredAsset
from app.models.receipt import RegistrationReceipt
from app.models.audit import AuditLog
from storage.local import LocalStorageProvider
import storage


import os

# Database configuration: defaults to in-memory SQLite, or connects to an isolated PostgreSQL test database
raw_test_url = os.getenv("TEST_DATABASE_URL")
raw_db_url = os.getenv("DATABASE_URL")

# Resolve selected test database URL safely
if raw_test_url:
    selected_url = raw_test_url.strip()
elif raw_db_url and "test" in raw_db_url.split("/")[-1].split("?")[0].lower():
    # Only allow DATABASE_URL if the database name explicitly contains 'test'
    selected_url = raw_db_url.strip()
else:
    selected_url = "sqlite:///:memory:"

is_sqlite = selected_url.startswith("sqlite")

# Safety Check: For any non-SQLite database, require explicit 'test' in the database name
if not is_sqlite:
    db_name = selected_url.split("/")[-1].split("?")[0].lower()
    if "test" not in db_name:
        raise RuntimeError(
            f"SAFETY ERROR: Refusing to run tests against database '{db_name}'. "
            "Dedicated test database name must explicitly contain 'test' (e.g. 'creditmera_test') "
            "to prevent accidental connection to or deletion of production data."
        )
    if selected_url.startswith("postgresql://"):
        selected_url = selected_url.replace("postgresql://", "postgresql+psycopg2://", 1)

TEST_DB_URL = selected_url

engine_kwargs = {}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = StaticPool
else:
    engine_kwargs["pool_pre_ping"] = True

test_engine = create_engine(TEST_DB_URL, **engine_kwargs)

# Enforce foreign key constraints on SQLite only
if is_sqlite:
    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    """Create all tables once for the test session and cleanly dispose engine on exit."""
    print(f"\n[TEST_DB_INFO] Dialect: {test_engine.dialect.name}, Database: {test_engine.url.database}")
    import app.db.session
    import app.services.job_service
    orig_session_local = app.db.session.SessionLocal
    app.db.session.SessionLocal = TestingSessionLocal
    app.services.job_service.SessionLocal = TestingSessionLocal
    Base.metadata.create_all(bind=test_engine)
    yield
    try:
        Base.metadata.drop_all(bind=test_engine)
    finally:
        app.db.session.SessionLocal = orig_session_local
        app.services.job_service.SessionLocal = orig_session_local
        test_engine.dispose()


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Provide a database session with guaranteed rollback and closure."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(autouse=True)
def clean_tables_between_tests(db: Session):
    """Ensure assets and receipts are wiped between test cases for isolation."""
    yield
    try:
        from app.models.job import AsyncJob
        db.query(AsyncJob).delete()
        db.query(RegistrationReceipt).delete()
        db.query(AuditLog).delete()
        db.query(RegisteredAsset).delete()
        db.commit()
    except Exception:
        db.rollback()



@pytest.fixture
def temp_storage_dir() -> Generator[Path, None, None]:
    """Temporary storage directory for testing."""
    temp_dir = Path(tempfile.mkdtemp(prefix="creditmera_test_storage_"))
    original_storage = storage.get_storage()
    test_storage = LocalStorageProvider(base_dir=temp_dir)
    storage.get_storage = lambda: test_storage

    yield temp_dir

    storage.get_storage = lambda: original_storage
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client(db: Session, temp_storage_dir: Path) -> Generator[TestClient, None, None]:
    """FastAPI test client with database and storage overrides."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def settings():
    """Returns current settings."""
    return get_settings()


@pytest.fixture
def test_user(db: Session) -> User:
    """Create and return a primary test user (retrieves if already exists)."""
    user = db.query(User).filter(User.email == "testowner@example.com").first()
    if not user:
        user = User(
            email="testowner@example.com",
            hashed_password=hash_password("SuperSecret123!"),
            full_name="Original Creator",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@pytest.fixture
def test_user_token(test_user: User) -> str:
    """JWT bearer token for test_user."""
    return create_access_token({"sub": test_user.id, "email": test_user.email})


@pytest.fixture
def another_user(db: Session) -> User:
    """Create and return a second test user for authorization testing."""
    user = db.query(User).filter(User.email == "attacker@example.com").first()
    if not user:
        user = User(
            email="attacker@example.com",
            hashed_password=hash_password("AttackerPass123!"),
            full_name="Malicious Adversary",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@pytest.fixture
def another_user_token(another_user: User) -> str:
    """JWT bearer token for another_user."""
    return create_access_token({"sub": another_user.id, "email": another_user.email})


@pytest.fixture
def sample_image_bytes() -> bytes:
    """Generate a clean synthetic 128x128 RGB test image in PNG format."""
    rng = np.random.default_rng(42)
    x = np.linspace(0, 1, 128)
    y = np.linspace(0, 1, 128)
    xx, yy = np.meshgrid(x, y)
    r = (np.sin(xx * 10) * 127 + 128).astype(np.uint8)
    g = (np.cos(yy * 10) * 127 + 128).astype(np.uint8)
    b = ((xx + yy) * 127).astype(np.uint8)
    img_array = np.stack([r, g, b], axis=-1)

    img = Image.fromarray(img_array, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
