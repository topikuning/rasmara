"""Smoke test M3: Contract CRUD, gate aktivasi, state machine, scope."""
from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.core.models import Role
from apps.master.models import Company, MasterFacility, PPK


@pytest.fixture(autouse=True)
def setup_roles(db):
    for code, name in [("superadmin", "Superadmin"), ("ppk", "PPK"),
                        ("kontraktor", "Kontraktor"), ("viewer", "Viewer")]:
        Role.objects.get_or_create(code=code, defaults={"name": name, "is_system": True})


@pytest.fixture
def superadmin(db, django_user_model):
    role = Role.objects.get(code="superadmin")
    u = django_user_model.objects.create(
        username="admin", full_name="Admin", role=role,
        is_superuser=True, is_staff=True,
    )
    u.set_password("Passw0rd!")
    u.save()
    return u


@pytest.fixture
def auth(superadmin):
    c = APIClient()
    c.force_authenticate(superadmin)
    return c


@pytest.fixture
def ppk(db):
    return PPK.objects.create(nip="198001012005011001", full_name="Drs Ahmad")


@pytest.fixture
def kontraktor(db):
    return Company.objects.create(code="K1", name="PT Kontraktor", type="KONTRAKTOR")


@pytest.fixture
def konsultan(db):
    return Company.objects.create(code="MK1", name="PT Konsultan MK", type="KONSULTAN")


@pytest.fixture
def master_facility(db):
    return MasterFacility.objects.create(code="GB", name="Gudang Beku")


@pytest.fixture
def contract_payload(ppk, kontraktor):
    return {
        "number": "001/KONTRAK/IV/2026",
        "name": "Pembangunan Gudang Beku Wilayah Timur",
        "ppk": str(ppk.id),
        "contractor": str(kontraktor.id),
        "fiscal_year": 2026,
        "original_value": "1000000000.00",
        "ppn_pct": "11.00",
        "start_date": "2026-04-01",
        "end_date": "2026-12-31",
    }


def test_create_contract_with_duration(auth, contract_payload, db):
    resp = auth.post("/api/v1/contracts/", contract_payload, format="json")
    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body["status"] == "DRAFT"
    assert body["duration_days"] == (date(2026, 12, 31) - date(2026, 4, 1)).days + 1
    # current_value mirror original_value saat create
    assert body["current_value"] == "1000000000.00"


def test_invalid_date_rejected(auth, contract_payload, db):
    contract_payload["end_date"] = "2026-03-01"  # < start_date
    resp = auth.post("/api/v1/contracts/", contract_payload, format="json")
    assert resp.status_code == 400
    assert "end_date" in str(resp.json())


def test_activation_blocked_without_locations(auth, contract_payload, db):
    r = auth.post("/api/v1/contracts/", contract_payload, format="json")
    cid = r.json()["id"]
    # Cek gate
    g = auth.get(f"/api/v1/contracts/{cid}/evaluate-gates/")
    assert g.status_code == 200
    assert g.json()["ok"] is False
    # Coba aktivasi → harus 409
    a = auth.post(f"/api/v1/contracts/{cid}/activate/", {}, format="json")
    assert a.status_code in (400, 409), a.json()


def test_activation_blocked_without_facility(auth, contract_payload, konsultan, db):
    r = auth.post("/api/v1/contracts/", contract_payload, format="json")
    cid = r.json()["id"]
    # Tambah lokasi dengan koordinat
    auth.post("/api/v1/locations/", {
        "contract": cid, "code": "L1",
        "name_desa": "Desa A", "name_kecamatan": "Kec A",
        "name_kota": "Kota A", "name_provinsi": "Prov A",
        "latitude": "-6.2000", "longitude": "106.8000",
        "konsultan": str(konsultan.id),
    }, format="json")
    # Cek gate — masih gagal karena belum ada fasilitas + BOQ
    g = auth.get(f"/api/v1/contracts/{cid}/evaluate-gates/")
    body = g.json()
    assert body["ok"] is False
    codes = {c["code"] for c in body["checks"] if not c["ok"]}
    assert "FACILITY_REQUIRED" in codes or "BOQ_V0_REQUIRED" in codes


def test_activation_bypass_via_godmode_only_superuser(
    auth, contract_payload, konsultan, master_facility, db,
):
    r = auth.post("/api/v1/contracts/", contract_payload, format="json")
    cid = r.json()["id"]
    # Tambah lokasi + fasilitas
    rl = auth.post("/api/v1/locations/", {
        "contract": cid, "code": "L1",
        "latitude": "-6.2", "longitude": "106.8",
        "konsultan": str(konsultan.id),
    }, format="json")
    lid = rl.json()["id"]
    auth.post("/api/v1/facilities/", {
        "location": lid, "code": "F1",
        "master_facility": str(master_facility.id),
        "name": "Gudang Beku 1",
    }, format="json")
    # Aktifkan dengan bypass_gate (superadmin OK)
    a = auth.post(f"/api/v1/contracts/{cid}/activate/",
                    {"bypass_gate": True}, format="json")
    assert a.status_code == 200, a.json()
    assert a.json()["status"] == "ACTIVE"


def test_state_machine_invalid_transition(auth, contract_payload, db):
    r = auth.post("/api/v1/contracts/", contract_payload, format="json")
    cid = r.json()["id"]
    # DRAFT -> COMPLETED dilarang
    resp = auth.post(f"/api/v1/contracts/{cid}/complete/", {}, format="json")
    assert resp.status_code in (400, 409)


def test_unique_location_code_per_contract(auth, contract_payload, db):
    r = auth.post("/api/v1/contracts/", contract_payload, format="json")
    cid = r.json()["id"]
    auth.post("/api/v1/locations/", {
        "contract": cid, "code": "DUP",
        "latitude": "-6", "longitude": "106",
    }, format="json")
    r2 = auth.post("/api/v1/locations/", {
        "contract": cid, "code": "DUP",
        "latitude": "-7", "longitude": "107",
    }, format="json")
    assert r2.status_code == 400


def test_summary_endpoint(auth, contract_payload, db):
    r = auth.post("/api/v1/contracts/", contract_payload, format="json")
    cid = r.json()["id"]
    s = auth.get(f"/api/v1/contracts/{cid}/summary/")
    assert s.status_code == 200
    body = s.json()
    assert body["status"] == "DRAFT"
    assert body["location_count"] == 0
    assert body["gates_ok"] is False


def test_godmode_set_and_clear(auth, contract_payload, db):
    r = auth.post("/api/v1/contracts/", contract_payload, format="json")
    cid = r.json()["id"]
    g = auth.post(f"/api/v1/contracts/{cid}/godmode/",
                    {"hours": 1, "reason": "Perbaikan data lapangan"}, format="json")
    assert g.status_code == 200, g.json()
    assert g.json()["is_godmode_active"] is True
    d = auth.delete(f"/api/v1/contracts/{cid}/godmode/")
    assert d.status_code == 200
    assert d.json()["is_godmode_active"] is False
