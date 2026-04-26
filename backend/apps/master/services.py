"""Service master data: auto-provisioning user (Inv. 15)."""
import re
import secrets
import string

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.core.models import Role

User = get_user_model()


def _generate_password(length: int = 12) -> str:
    """Generate password random alphanumeric + punct (tanpa karakter ambigu)."""
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    # hindari I, l, 1, O, 0
    alphabet = alphabet.translate(str.maketrans("", "", "Il1O0"))
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _slugify_username(base: str) -> str:
    """Bersihkan string jadi username-friendly."""
    s = re.sub(r"[^a-zA-Z0-9_]", "_", base.strip().lower())
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:60] or "user"


def _unique_username(candidate: str) -> str:
    """Tambahkan suffix angka kalau username sudah dipakai."""
    base = candidate
    n = 1
    while User.objects.filter(username=candidate).exists():
        n += 1
        candidate = f"{base}{n}"
    return candidate


@transaction.atomic
def provision_company_user(company, role_code: str = "kontraktor") -> tuple[User, str]:
    """Auto-provision user default untuk Company.

    Returns: (user, plain_password) — caller bertugas tampilkan password
    sekali ke admin yang membuat company.
    """
    if company.default_user_id:
        # sudah ada
        return company.default_user, ""

    role = Role.objects.filter(code=role_code).first()
    if role is None:
        # fallback ke 'kontraktor' atau viewer
        role = Role.objects.filter(code="viewer").first()

    username = _unique_username(_slugify_username(company.code or company.name))
    password = _generate_password()

    user = User(
        username=username,
        email=company.email or f"{username}@rasmara.local",
        full_name=company.pic_name or company.name,
        phone=company.pic_phone or company.phone,
        role=role,
        is_active=True,
        must_change_password=True,
        auto_provisioned=True,
    )
    user.set_password(password)
    user.save()

    company.default_user = user
    company.save(update_fields=["default_user", "updated_at"])

    return user, password


@transaction.atomic
def provision_ppk_user(ppk, role_code: str = "ppk") -> tuple[User, str]:
    """Auto-provision user untuk PPK."""
    if ppk.user_id:
        return ppk.user, ""

    role = Role.objects.filter(code=role_code).first()
    if role is None:
        role = Role.objects.filter(code="viewer").first()

    # base username = first part NIP atau slug nama
    base = ppk.nip or _slugify_username(ppk.full_name)
    username = _unique_username(_slugify_username(base))
    password = _generate_password()

    user = User(
        username=username,
        email=ppk.email or f"{username}@rasmara.local",
        full_name=ppk.full_name,
        phone=ppk.whatsapp,
        role=role,
        is_active=True,
        must_change_password=True,
        auto_provisioned=True,
    )
    user.set_password(password)
    user.save()

    ppk.user = user
    ppk.save(update_fields=["user", "updated_at"])

    return user, password
