"""Smoke test M2: Company create + auto-provision user, PPK, MasterFacility."""
import pytest
from rest_framework.test import APIClient

from apps.core.models import Permission, Role


@pytest.fixture
def superadmin(db, django_user_model):
    role, _ = Role.objects.get_or_create(code="superadmin",
                                          defaults={"name": "Superadmin", "is_system": True})
    u = django_user_model.objects.create(
        username="admin", full_name="Admin", role=role,
        is_superuser=True, is_staff=True,
    )
    u.set_password("Passw0rd!")
    u.save()
    return u


@pytest.fixture
def auth_client(superadmin):
    c = APIClient()
    c.force_authenticate(superadmin)
    return c


@pytest.fixture(autouse=True)
def setup_roles(db):
    """Seed minimal: role kontraktor & ppk wajib utk auto-provision."""
    Role.objects.get_or_create(code="kontraktor", defaults={"name": "Kontraktor", "is_system": True})
    Role.objects.get_or_create(code="ppk", defaults={"name": "PPK", "is_system": True})
    Role.objects.get_or_create(code="viewer", defaults={"name": "Viewer", "is_system": True})


def test_company_create_auto_provisions_user(auth_client, db):
    payload = {
        "code": "PT-ABC",
        "name": "PT ABC Konstruksi",
        "type": "KONTRAKTOR",
        "npwp": "12.345.678.9-012.345",
        "email": "abc@example.com",
        "pic_name": "Budi Santoso",
        "pic_phone": "6281234567890",
    }
    resp = auth_client.post("/api/v1/companies/", payload, format="json")
    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body["code"] == "PT-ABC"
    assert body["default_user"] is not None
    assert "initial_user" in body
    assert body["initial_user"]["must_change_password"] is True
    assert body["initial_user"]["initial_password"]


def test_company_lookup(auth_client, db):
    auth_client.post("/api/v1/companies/",
                      {"code": "C1", "name": "Company One", "type": "KONTRAKTOR"},
                      format="json")
    resp = auth_client.get("/api/v1/companies/lookup/?search=One")
    assert resp.status_code == 200
    data = resp.json()
    assert any(c["code"] == "C1" for c in data)


def test_ppk_create_auto_provisions_user(auth_client, db):
    payload = {
        "nip": "198001012005011001",
        "full_name": "Drs. Ahmad PPK",
        "jabatan": "PPK Direktorat XYZ",
        "satker": "Direktorat XYZ",
        "whatsapp": "6281000000000",
        "email": "ppk@example.go.id",
    }
    resp = auth_client.post("/api/v1/ppks/", payload, format="json")
    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body["nip"] == "198001012005011001"
    assert body["user"] is not None
    assert "initial_user" in body


def test_master_facility_crud(auth_client, db):
    # need master.update perm; superadmin bypass
    resp = auth_client.post("/api/v1/master-facilities/",
                              {"code": "GB", "name": "Gudang Beku"},
                              format="json")
    assert resp.status_code == 201, resp.json()
    fac_id = resp.json()["id"]

    resp = auth_client.patch(f"/api/v1/master-facilities/{fac_id}/",
                              {"description": "Gudang penyimpanan beku -25C"},
                              format="json")
    assert resp.status_code == 200

    resp = auth_client.get("/api/v1/master-facilities/lookup/")
    assert resp.status_code == 200
    assert any(x["code"] == "GB" for x in resp.json())


def test_company_soft_delete(auth_client, db):
    r1 = auth_client.post("/api/v1/companies/",
                           {"code": "DEL", "name": "ToDelete", "type": "OTHER"},
                           format="json")
    cid = r1.json()["id"]
    r2 = auth_client.delete(f"/api/v1/companies/{cid}/")
    assert r2.status_code == 204
    # tidak muncul di list default (soft-delete filter)
    r3 = auth_client.get("/api/v1/companies/")
    ids = [c["id"] for c in r3.json()["results"]]
    assert cid not in ids
