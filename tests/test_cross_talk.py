import pytest

from orcanium.app.core.db import Base, CrossTalkRequest
from orcanium.app.domains.capability.cross_talk import (
    request_cross_talk, resolve_cross_talk,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session


def test_cross_talk_requires_resolution(db):
    request = request_cross_talk(db, "a", "b", "Please summarize this")
    assert request.status == "pending_permission"
    resolve_cross_talk(db, request.id, True)
    assert db.get(CrossTalkRequest, request.id).status == "approved"


def test_cross_talk_context_is_bounded(db):
    request = request_cross_talk(db, "a", "b", "hello", context_summary="x" * 10000)
    assert len(request.context_summary) == 8000


def test_cross_talk_rejects_self_and_empty_requests(db):
    with pytest.raises(ValueError):
        request_cross_talk(db, "a", "a", "hello")
    with pytest.raises(ValueError):
        request_cross_talk(db, "a", "b", "  ")
