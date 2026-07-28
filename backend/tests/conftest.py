import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_scenario_id():
    return "networking_event"


@pytest.fixture
def user_id():
    return "test-user-id"
