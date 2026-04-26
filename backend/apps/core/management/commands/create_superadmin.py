"""Create / update superadmin user.

Sumber kredensial: env vars SUPERADMIN_USERNAME / SUPERADMIN_PASSWORD / SUPERADMIN_EMAIL,
bisa di-override via flag --username --password --email.

Idempotent: kalau user sudah ada, hanya update password & role bila --reset.
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.core.models import Role

User = get_user_model()


class Command(BaseCommand):
    help = "Buat (atau reset) superadmin user."

    def add_arguments(self, parser):
        parser.add_argument("--username", default=None)
        parser.add_argument("--password", default=None)
        parser.add_argument("--email", default=None)
        parser.add_argument("--reset", action="store_true",
                            help="Reset password walau user sudah ada.")

    def handle(self, *args, **opts):
        username = opts["username"] or os.environ.get("SUPERADMIN_USERNAME", "superadmin")
        password = opts["password"] or os.environ.get("SUPERADMIN_PASSWORD", "ChangeMe123!")
        email = opts["email"] or os.environ.get("SUPERADMIN_EMAIL", "superadmin@rasmara.local")

        role = Role.objects.filter(code="superadmin").first()
        if role is None:
            raise CommandError("Role 'superadmin' belum ada. Jalankan 'seed_initial_data' dulu.")

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "full_name": "Superadmin",
                "role": role,
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
                "must_change_password": True,
            },
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f"Superadmin dibuat: {username}. Password awal: {password}. "
                "WAJIB ganti password saat login pertama."
            ))
        elif opts["reset"]:
            user.set_password(password)
            user.is_active = True
            user.is_superuser = True
            user.is_staff = True
            user.must_change_password = True
            user.role = role
            user.save()
            self.stdout.write(self.style.WARNING(
                f"Password superadmin '{username}' di-reset ke '{password}'."
            ))
        else:
            self.stdout.write(self.style.NOTICE(
                f"Superadmin '{username}' sudah ada. Pakai --reset untuk reset password."
            ))
