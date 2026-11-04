import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.security import limiter
from conftest import synthetic_daily

BOUNDARY = {"type": "Polygon", "coordinates": [[
    [38.980, 8.750], [38.990, 8.750], [38.990, 8.758], [38.980, 8.758], [38.980, 8.750],
]]}
NEW = {"farmer_name": "Test Farmer", "farmer_ref": "F-001", "crop": "wheat", "soil": "loam",
       "planting_month": 6, "planting_day": 15, "loan_amount_etb": 30000, "boundary": BOUNDARY}


@pytest.fixture(scope="module")
def client():
    with TestClient(main.app) as c:
        yield c


@pytest.fixture(autouse=True)
def fake_climate(monkeypatch):
    calls = []

    def fake_field_daily(db, points, today=None, fetch=None):
        calls.append(points)
        return synthetic_daily(), [(8.5, 38.75)]

    monkeypatch.setattr(main, "field_daily", fake_field_daily)
    return calls


def login(client, email="admin@example.com", password="admin-password-123"):
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


@pytest.fixture(scope="module")
def admin(client):
    return login(client)


@pytest.fixture(scope="module")
def officer(client, admin):
    res = client.post("/users", headers=admin, json={
        "email": "officer@example.com", "name": "Officer One", "password": "officer-pass-123"})
    assert res.status_code == 201, res.text
    return login(client, "officer@example.com", "officer-pass-123")


def test_health_is_open(client):
    body = client.get("/health").json()
    assert body == {"status": "ok", "database": True, "ai_available": False}


def test_protected_routes_need_a_token(client):
    assert client.get("/reference").status_code == 401
    assert client.get("/assessments").status_code == 401
    assert client.get("/assessments", headers={"Authorization": "Bearer forged.token"}).status_code == 401


def test_wrong_password_and_lockout(client):
    limiter.succeeded("admin@example.com")
    for _ in range(5):
        assert client.post("/auth/login", json={"email": "admin@example.com", "password": "nope"}).status_code == 401
    res = client.post("/auth/login", json={"email": "admin@example.com", "password": "admin-password-123"})
    assert res.status_code == 429
    limiter.succeeded("admin@example.com")


def test_reference_lists_crops_and_assumptions(client, admin):
    body = client.get("/reference", headers=admin).json()
    assert {c["key"] for c in body["crops"]} == {"wheat", "teff", "maize", "sorghum", "barley"}
    assert body["assumptions"]["lending"]["repayment_share"] == 0.4
    assert body["ai_available"] is False


def test_only_admins_manage_users(client, officer):
    assert client.get("/users", headers=officer).status_code == 403
    assert client.post("/users", headers=officer, json={
        "email": "x@example.com", "name": "X", "password": "long-enough-1"}).status_code == 403


def test_create_assessment_from_boundary(client, officer, fake_climate):
    res = client.post("/assessments", headers=officer, json=NEW)
    assert res.status_code == 201, res.text
    a = res.json()
    field = a["result"]["field"]
    assert field["area_source"] == "boundary"
    assert field["area_ha"] == pytest.approx(97.7, rel=0.01)  # 0.01 deg x 0.008 deg at 8.75 N
    assert a["boundary"] == BOUNDARY
    assert a["risk_rating"] in {"Low", "Medium", "High"}
    assert a["result"]["climate"]["years"] == 42
    assert len(a["result"]["insurance"]["years"]) == 42
    # The four corners and the centre are sampled for rainfall.
    assert len(fake_climate[-1]) == 5
    assert a["summary_text"] is None


def test_create_assessment_from_point_and_area(client, officer):
    body = {**NEW, "boundary": None, "lat": 8.75, "lon": 38.98, "area_ha": 1.5}
    a = client.post("/assessments", headers=officer, json=body).json()
    assert a["area_ha"] == 1.5 and a["result"]["field"]["area_source"] == "entered"


@pytest.mark.parametrize("change, message", [
    ({"boundary": None}, "Draw the field boundary"),
    ({"planting_month": 2, "planting_day": 30}, "does not exist"),
    ({"boundary": {"type": "Point", "coordinates": [38.9, 8.7]}}, "GeoJSON Polygon"),
    ({"trigger_percentile": 20, "exit_percentile": 25}, "exit percentile"),
])
def test_invalid_input_is_rejected(client, officer, change, message):
    res = client.post("/assessments", headers=officer, json={**NEW, **change})
    assert res.status_code == 422
    assert message in res.text


def test_officers_only_see_their_own(client, admin, officer):
    mine = client.post("/assessments", headers=admin, json={**NEW, "farmer_name": "Admin's farmer"}).json()
    officer_list = client.get("/assessments", headers=officer).json()
    assert all(a["created_by"] == "Officer One" for a in officer_list)
    assert client.get(f"/assessments/{mine['id']}", headers=officer).status_code == 404
    admin_list = client.get("/assessments", headers=admin).json()
    assert {a["created_by"] for a in admin_list} >= {"Officer One", "Administrator"}


def test_summary_needs_a_key(client, officer):
    a = client.get("/assessments", headers=officer).json()[0]
    res = client.post(f"/assessments/{a['id']}/summary", headers=officer, json={"language": "en"})
    assert res.status_code == 503


def test_summary_is_saved(client, officer, monkeypatch):
    seen = {}

    def fake_summarise(assessment, language, api_key=None):
        seen["language"], seen["farmer"] = language, assessment["farmer_name"]
        return {"text": "Overall:\n- fine", "model": "claude-opus-5-5", "language": "Amharic"}

    monkeypatch.setattr(main, "summarise", fake_summarise)
    monkeypatch.setattr(main.get_settings(), "anthropic_api_key", "test-key")
    a = client.get("/assessments", headers=officer).json()[0]
    res = client.post(f"/assessments/{a['id']}/summary", headers=officer, json={"language": "am"})
    assert res.status_code == 200, res.text
    assert seen == {"language": "am", "farmer": a["farmer_name"]}
    again = client.get(f"/assessments/{a['id']}", headers=officer).json()
    assert again["summary_text"].startswith("Overall:") and again["summary_language"] == "Amharic"


def test_password_change_signs_out_old_sessions(client):
    client.post("/users", headers=login(client), json={
        "email": "temp@example.com", "name": "Temp", "password": "temp-password-1"})
    old = login(client, "temp@example.com", "temp-password-1")
    res = client.post("/auth/password", headers=old, json={
        "current_password": "temp-password-1", "new_password": "temp-password-2"})
    assert res.status_code == 204
    assert client.get("/auth/me", headers=old).status_code == 401
    assert login(client, "temp@example.com", "temp-password-2")



def test_no_demo_account_unless_switched_on(client):
    assert client.get("/auth/demo").json() == {"enabled": False}
    assert client.post("/auth/demo").status_code == 404


def test_demo_account_is_walled_off(client, admin, officer, monkeypatch):
    client.post("/assessments", headers=officer, json=NEW)  # someone else's data
    monkeypatch.setattr(main.get_settings(), "demo_account", True)
    with main.SessionLocal() as db:
        main.seed_demo(db)
        main.seed_demo(db)  # running again on the next start-up is harmless
    assert client.get("/auth/demo").json() == {"enabled": True}
    headers = {"Authorization": f"Bearer {client.post('/auth/demo').json()['token']}"}

    me = client.get("/auth/me", headers=headers).json()
    assert me["role"] == "admin"
    # No password sign-in, and nothing to change.
    assert client.post("/auth/login", json={"email": me["email"], "password": ""}).status_code == 422
    assert client.post("/auth/password", headers=headers, json={
        "current_password": "x", "new_password": "taken-over-123"}).status_code == 403
    # Sees only itself and its own assessments; cannot add accounts.
    assert [u["email"] for u in client.get("/users", headers=headers).json()] == [me["email"]]
    assert client.get("/assessments", headers=headers).json() == []
    others = client.get("/assessments", headers=admin).json()
    assert others and client.get(f"/assessments/{others[0]['id']}", headers=headers).status_code == 404
    assert client.post("/users", headers=headers, json={
        "email": "new@example.com", "name": "New", "password": "long-enough-1"}).status_code == 403
    created = client.post("/assessments", headers=headers, json=NEW)
    assert created.status_code == 201
    assert len(client.get("/assessments", headers=headers).json()) == 1
