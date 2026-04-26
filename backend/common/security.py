"""Util keamanan ringan: generate password random untuk auto-provisioning & reset.

Kenapa pakai ini, bukan User.objects.make_random_password()?
  -> Django 4.1+ menghapus make_random_password dari BaseUserManager.

Karakter ambigu (I, l, 1, O, 0) dihindari supaya password mudah di-print &
diketik ulang oleh user di lapangan.
"""
import secrets
import string

_ALPHABET = (string.ascii_letters + string.digits + "!@#$%&*").translate(
    str.maketrans("", "", "Il1O0")
)


def generate_password(length: int = 12) -> str:
    """Generate password random alfanumerik + sebagian simbol, panjang default 12."""
    if length < 6:
        length = 6
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))
