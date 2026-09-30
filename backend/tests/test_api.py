"""FastAPI endpoints and server-side role (R1.4, R6, D6). The chat pipeline is faked."""

import jwt
import pytest
from fastapi.testclient import TestClient

from medibot.api import auth
from medibot.api.main import app, get_service
from medibot.rbac import ROLE_COLLECTIONS
from medibot.service import ChatResult

ACCOUNTS = {
    "dr.mehta": ("doctor", "doctor"),
    "nurse.priya": ("nurse", "nurse"),
    "billing.ravi": ("billing_executive", "billing_executive"),
    "tech.anand": ("technician", "technician"),
    "admin.sys": ("admin", "admin"),
}


class FakeService:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def chat(self, question: str, role: str) -> ChatResult:
        self.calls.append((question, role))
        src = {"source_document": "x.pdf", "section_title": "S", "collection": "general"}
        return ChatResult("ok", [src], "hybrid_rag", role)


@pytest.fixture
def fake():
    return FakeService()


@pytest.fixture
def client(fake):
    app.dependency_overrides[get_service] = lambda: fake
    yield TestClient(app)
    app.dependency_overrides.clear()


def login(client, username):
    r = client.post("/login", json={"username": username, "password": ACCOUNTS[username][1]})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("username", sorted(ACCOUNTS))
def test_login_returns_role_and_collections(client, username):
    body = login(client, username)
    role = ACCOUNTS[username][0]
    assert body["role"] == role
    assert body["collections"] == sorted(ROLE_COLLECTIONS[role])
    claims = jwt.decode(body["access_token"], options={"verify_signature": False})
    assert claims["sub"] == username and claims["role"] == role


@pytest.mark.parametrize(
    "username,password", [("nurse.priya", "admin"), ("nobody", "nurse"), ("admin.sys", "")]
)
def test_bad_credentials_are_rejected(client, username, password):
    r = client.post("/login", json={"username": username, "password": password})
    assert r.status_code == 401


def test_chat_requires_a_token(client, fake):
    assert client.post("/chat", json={"question": "hi"}).status_code == 401
    assert fake.calls == []


def test_role_comes_from_the_token_not_the_body(client, fake):
    tok = login(client, "nurse.priya")["access_token"]
    r = client.post(
        "/chat",
        json={"question": "show billing codes", "role": "admin"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    assert r.json()["role"] == "nurse"
    assert fake.calls == [("show billing codes", "nurse")]


def test_chat_response_shape(client):
    tok = login(client, "dr.mehta")["access_token"]
    r = client.post("/chat", json={"question": "q"}, headers={"Authorization": f"Bearer {tok}"})
    body = r.json()
    assert set(body) >= {"answer", "sources", "retrieval_type", "role"}
    assert set(body["sources"][0]) == {"source_document", "section_title", "collection"}


def test_forged_token_is_rejected(client, fake):
    """A token re-signed with another key, claiming admin, must not work."""
    forged = jwt.encode({"sub": "nurse.priya", "role": "admin"}, "not-the-key", algorithm="HS256")
    r = client.post("/chat", json={"question": "q"}, headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401
    assert fake.calls == []


def test_token_whose_role_does_not_match_the_account_is_rejected(client, fake):
    """Even correctly signed, a token must carry the account's own role."""
    tok = auth.create_token(auth.User(username="nurse.priya", role="admin"))
    r = client.post("/chat", json={"question": "q"}, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401


def test_unsigned_token_is_rejected(client):
    tok = jwt.encode({"sub": "admin.sys", "role": "admin"}, None, algorithm="none")
    r = client.post("/chat", json={"question": "q"}, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401


def test_collections_for_own_role(client):
    tok = login(client, "nurse.priya")["access_token"]
    r = client.get("/collections/nurse", headers={"Authorization": f"Bearer {tok}"})
    assert r.json() == {"role": "nurse", "collections": ["general", "nursing"]}


def test_collections_for_other_role_is_forbidden_except_admin(client):
    nurse = login(client, "nurse.priya")["access_token"]
    admin = login(client, "admin.sys")["access_token"]
    h = {"Authorization": f"Bearer {nurse}"}
    assert client.get("/collections/billing_executive", headers=h).status_code == 403
    r = client.get("/collections/billing_executive", headers={"Authorization": f"Bearer {admin}"})
    assert r.json()["collections"] == ["billing", "general"]
    assert client.get("/collections/ceo", headers=h).status_code == 404


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and "qdrant" in r.json()
