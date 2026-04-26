"""Smoke test M4: BOQ V0 auto-create, item CRUD, recompute, validate budget."""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.contract.models import Contract, Facility, Location
from apps.core.models import Role
from apps.master.models import Company, MasterFacility, PPK


@pytest.fixture(autouse=True)
def setup(db):
    for code, name in [("superadmin", "Super"), ("ppk", "PPK"),
                        ("kontraktor", "Kont"), ("viewer", "View")]:
        Role.objects.get_or_create(code=code, defaults={"name": name, "is_system": True})


@pytest.fixture
def admin(db, django_user_model):
    role = Role.objects.get(code="superadmin")
    u = django_user_model.objects.create(
        username="admin", full_name="Admin", role=role,
        is_superuser=True, is_staff=True,
    )
    u.set_password("Pwd!")
    u.save()
    return u


@pytest.fixture
def auth(admin):
    c = APIClient()
    c.force_authenticate(admin)
    return c


@pytest.fixture
def contract(db):
    ppk = PPK.objects.create(nip="111", full_name="P")
    kontr = Company.objects.create(code="K", name="K", type="KONTRAKTOR")
    return Contract.objects.create(
        number="C001", name="Test", ppk=ppk, contractor=kontr,
        fiscal_year=2026,
        original_value=Decimal("1000000000"),
        current_value=Decimal("1000000000"),
        ppn_pct=Decimal("11"),
        start_date="2026-01-01", end_date="2026-12-31",
    )


@pytest.fixture
def loc_with_facility(db, contract):
    loc = Location.objects.create(
        contract=contract, code="L1",
        latitude=Decimal("-6"), longitude=Decimal("106"),
    )
    mf = MasterFacility.objects.create(code="GB", name="Gudang Beku")
    fac = Facility.objects.create(location=loc, code="F1", name="GB1", master_facility=mf)
    return fac


def test_v0_auto_created_on_contract_create(contract):
    from apps.boq.models import BOQRevision
    revs = BOQRevision.objects.filter(contract=contract)
    assert revs.count() == 1
    v0 = revs.first()
    assert v0.version == 0
    assert v0.is_active is True
    assert v0.status == "DRAFT"


def test_create_boq_item(auth, contract, loc_with_facility):
    from apps.boq.models import BOQRevision
    rev = BOQRevision.objects.get(contract=contract, version=0)

    payload = {
        "boq_revision": str(rev.id),
        "facility": str(loc_with_facility.id),
        "code": "1",
        "description": "Pekerjaan persiapan",
        "unit": "ls",
        "volume": "1",
        "unit_price": "5000000",
    }
    r = auth.post("/api/v1/boq-items/", payload, format="json")
    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["total_price"] == "5000000.00"
    assert body["is_leaf"] is True


def test_validate_budget_ok_when_under(auth, contract, loc_with_facility):
    from apps.boq.models import BOQRevision
    rev = BOQRevision.objects.get(contract=contract, version=0)

    auth.post("/api/v1/boq-items/", {
        "boq_revision": str(rev.id),
        "facility": str(loc_with_facility.id),
        "code": "1",
        "description": "Beton",
        "unit": "m3",
        "volume": "100",
        "unit_price": "1000000",  # total 100M, post-PPN 111M, masih < 1M
    }, format="json")

    r = auth.post(f"/api/v1/boq-revisions/{rev.id}/validate-budget/", {}, format="json")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert Decimal(body["boq_pre_ppn"]) == Decimal("100000000.00")


def test_validate_budget_fails_when_over(auth, contract, loc_with_facility):
    from apps.boq.models import BOQRevision
    rev = BOQRevision.objects.get(contract=contract, version=0)

    # Total post-PPN = 1.1B * 1.11 > 1B kontrak
    auth.post("/api/v1/boq-items/", {
        "boq_revision": str(rev.id),
        "facility": str(loc_with_facility.id),
        "code": "1",
        "description": "Mahal",
        "unit": "ls",
        "volume": "1",
        "unit_price": "1000000000",
    }, format="json")

    r = auth.post(f"/api/v1/boq-revisions/{rev.id}/validate-budget/", {}, format="json")
    body = r.json()
    assert body["ok"] is False


def test_hierarchy_parent_total_aggregates(auth, contract, loc_with_facility):
    from apps.boq.models import BOQItem, BOQRevision
    rev = BOQRevision.objects.get(contract=contract, version=0)

    p = auth.post("/api/v1/boq-items/", {
        "boq_revision": str(rev.id), "facility": str(loc_with_facility.id),
        "code": "P", "description": "Parent", "unit": "", "volume": "0", "unit_price": "0",
    }, format="json").json()

    auth.post("/api/v1/boq-items/", {
        "boq_revision": str(rev.id), "facility": str(loc_with_facility.id),
        "code": "C1", "description": "Child 1", "unit": "ls",
        "volume": "1", "unit_price": "100", "parent": p["id"],
    }, format="json")
    auth.post("/api/v1/boq-items/", {
        "boq_revision": str(rev.id), "facility": str(loc_with_facility.id),
        "code": "C2", "description": "Child 2", "unit": "ls",
        "volume": "2", "unit_price": "200", "parent": p["id"],
    }, format="json")

    parent = BOQItem.objects.get(pk=p["id"])
    parent.refresh_from_db()
    # 1*100 + 2*200 = 500
    assert parent.total_price == Decimal("500.00")
    assert parent.is_leaf is False


def test_approve_locks_revision(auth, contract, loc_with_facility):
    from apps.boq.models import BOQRevision
    rev = BOQRevision.objects.get(contract=contract, version=0)

    auth.post("/api/v1/boq-items/", {
        "boq_revision": str(rev.id), "facility": str(loc_with_facility.id),
        "code": "X", "description": "X", "unit": "ls",
        "volume": "1", "unit_price": "1000",
    }, format="json")

    r = auth.post(f"/api/v1/boq-revisions/{rev.id}/approve/", {}, format="json")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "APPROVED"


def test_delete_parent_promotes_children(auth, contract, loc_with_facility):
    from apps.boq.models import BOQItem, BOQRevision
    rev = BOQRevision.objects.get(contract=contract, version=0)
    p = auth.post("/api/v1/boq-items/", {
        "boq_revision": str(rev.id), "facility": str(loc_with_facility.id),
        "code": "P", "description": "P", "unit": "", "volume": "0", "unit_price": "0",
    }, format="json").json()
    c = auth.post("/api/v1/boq-items/", {
        "boq_revision": str(rev.id), "facility": str(loc_with_facility.id),
        "code": "C", "description": "C", "unit": "ls",
        "volume": "1", "unit_price": "100", "parent": p["id"],
    }, format="json").json()

    r = auth.delete(f"/api/v1/boq-items/{p['id']}/")
    assert r.status_code == 204

    # Child harusnya masih ada, dengan parent=null
    child = BOQItem.objects.get(pk=c["id"])
    assert child.parent_id is None
