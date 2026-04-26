"""Smoke test M1: health, auth, RBAC dasar."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.core.models import Role


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def superadmin_user(db, django_user_model):
    role, _ = Role.objects.get_or_create(code="superadmin",
                                          defaults={"name": "Superadmin", "is_system": True})
    user = django_user_model.objects.create(
        username="admin", full_name="Admin", email="admin@x.com",
        role=role, is_superuser=True, is_staff=True,
    )
    user.set_password("Passw0rd!")
    user.save()
    return user


def test_health_open(client):
    resp = client.get("/api/v1/health/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_login_returns_token(client, superadmin_user):
    resp = client.post("/api/v1/auth/login",
                        {"username": "admin", "password": "Passw0rd!"}, format="json")
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert "access" in body
    assert "refresh" in body
    assert body["user"]["username"] == "admin"


def test_me_requires_auth(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_returns_profile(client, superadmin_user):
    client.force_authenticate(user=superadmin_user)
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "admin"
    assert body["is_superuser"] is True


def test_change_password_force_first_login(client, superadmin_user):
    superadmin_user.must_change_password = True
    superadmin_user.save()
    client.force_authenticate(user=superadmin_user)
    resp = client.post("/api/v1/auth/change-password",
                        {"new_password": "BrandNewSecret123!"}, format="json")
    assert resp.status_code == 200, resp.json()
    superadmin_user.refresh_from_db()
    assert not superadmin_user.must_change_password
    assert superadmin_user.check_password("BrandNewSecret123!")
