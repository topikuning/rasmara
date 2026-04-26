"""Seed data awal: permission catalog, role bawaan, menu tree.

Idempotent — bisa dijalankan berkali-kali tanpa duplikasi.
Run: python manage.py seed_initial_data
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Menu, Permission, Role


# Permission catalog. Format: (code, name, module, action, description)
PERMISSIONS: list[tuple[str, str, str, str, str]] = [
    # --- core ---
    ("user.read", "Lihat user", "user", "read", "Melihat daftar dan detail user."),
    ("user.create", "Buat user", "user", "create", "Membuat user baru."),
    ("user.update", "Ubah user", "user", "update", "Mengubah data user (termasuk reset password)."),
    ("user.delete", "Hapus user", "user", "delete", "Menonaktifkan/menghapus user."),
    ("role.read", "Lihat role", "role", "read", ""),
    ("role.create", "Buat role", "role", "create", ""),
    ("role.update", "Ubah role", "role", "update", "Termasuk set permission & menu."),
    ("role.delete", "Hapus role", "role", "delete", ""),
    ("menu.read", "Lihat menu", "menu", "read", ""),
    ("menu.create", "Buat menu", "menu", "create", ""),
    ("menu.update", "Ubah menu", "menu", "update", ""),
    ("menu.delete", "Hapus menu", "menu", "delete", ""),
    ("audit.read", "Lihat audit log", "audit", "read", ""),
    # --- master ---
    ("company.read", "Lihat perusahaan", "company", "read", ""),
    ("company.create", "Buat perusahaan", "company", "create", ""),
    ("company.update", "Ubah perusahaan", "company", "update", ""),
    ("company.delete", "Hapus perusahaan", "company", "delete", ""),
    ("ppk.read", "Lihat PPK", "ppk", "read", ""),
    ("ppk.create", "Buat PPK", "ppk", "create", ""),
    ("ppk.update", "Ubah PPK", "ppk", "update", ""),
    ("ppk.delete", "Hapus PPK", "ppk", "delete", ""),
    ("master.read", "Lihat master data", "master", "read", "Master Facility, Work Code."),
    ("master.update", "Ubah master data", "master", "update", ""),
    # --- contract ---
    ("contract.read", "Lihat kontrak", "contract", "read", ""),
    ("contract.create", "Buat kontrak", "contract", "create", "PPK & Admin & Superadmin (Inv. 17)."),
    ("contract.update", "Ubah kontrak", "contract", "update", ""),
    ("contract.delete", "Hapus kontrak", "contract", "delete", ""),
    ("contract.activate", "Aktivasi kontrak", "contract", "activate", "DRAFT -> ACTIVE."),
    ("contract.complete", "Selesaikan kontrak", "contract", "complete", ""),
    ("contract.terminate", "Hentikan kontrak", "contract", "terminate", ""),
    ("contract.hold", "Pause kontrak", "contract", "hold", ""),
    ("location.read", "Lihat lokasi", "location", "read", ""),
    ("location.create", "Buat lokasi", "location", "create", ""),
    ("location.update", "Ubah lokasi", "location", "update", ""),
    ("location.delete", "Hapus lokasi", "location", "delete", ""),
    ("facility.read", "Lihat fasilitas", "facility", "read", ""),
    ("facility.create", "Buat fasilitas", "facility", "create", ""),
    ("facility.update", "Ubah fasilitas", "facility", "update", ""),
    ("facility.delete", "Hapus fasilitas", "facility", "delete", ""),
    # --- BOQ ---
    ("boq.read", "Lihat BOQ", "boq", "read", ""),
    ("boq.create", "Buat BOQ", "boq", "create", ""),
    ("boq.update", "Ubah BOQ", "boq", "update", ""),
    ("boq.delete", "Hapus BOQ item", "boq", "delete", ""),
    ("boq.approve", "Approve revisi BOQ", "boq", "approve", ""),
    ("boq.import", "Import BOQ", "boq", "import", "Import dari Excel."),
    # --- VO ---
    ("vo.read", "Lihat VO", "vo", "read", ""),
    ("vo.create", "Buat VO", "vo", "create", ""),
    ("vo.update", "Ubah VO", "vo", "update", ""),
    ("vo.delete", "Hapus VO", "vo", "delete", ""),
    ("vo.submit", "Submit VO", "vo", "submit", "DRAFT -> UNDER_REVIEW."),
    ("vo.approve", "Approve VO", "vo", "approve", ""),
    ("vo.reject", "Reject VO", "vo", "reject", ""),
    # --- MC (Field Observation) ---
    ("mc.read", "Lihat Berita Acara MC", "mc", "read", ""),
    ("mc.create", "Buat MC", "mc", "create", ""),
    ("mc.update", "Ubah MC", "mc", "update", ""),
    ("mc.delete", "Hapus MC", "mc", "delete", ""),
    # --- addendum ---
    ("addendum.read", "Lihat addendum", "addendum", "read", ""),
    ("addendum.create", "Buat addendum", "addendum", "create", ""),
    ("addendum.update", "Ubah addendum", "addendum", "update", ""),
    ("addendum.delete", "Hapus addendum DRAFT", "addendum", "delete", ""),
    ("addendum.sign", "Tanda tangan addendum", "addendum", "sign", "Aksi legal."),
    # --- report harian ---
    ("report_daily.read", "Lihat laporan harian", "report_daily", "read", ""),
    ("report_daily.create", "Buat laporan harian", "report_daily", "create", ""),
    ("report_daily.update", "Ubah laporan harian", "report_daily", "update", ""),
    ("report_daily.delete", "Hapus laporan harian", "report_daily", "delete", ""),
    # --- report mingguan ---
    ("report_weekly.read", "Lihat laporan mingguan", "report_weekly", "read", ""),
    ("report_weekly.create", "Buat laporan mingguan", "report_weekly", "create", ""),
    ("report_weekly.update", "Ubah laporan mingguan", "report_weekly", "update", ""),
    ("report_weekly.delete", "Hapus laporan mingguan", "report_weekly", "delete", ""),
    ("report_weekly.lock", "Lock/unlock laporan mingguan", "report_weekly", "lock", ""),
    # --- field review ---
    ("review.read", "Lihat field review", "review", "read", ""),
    ("review.create", "Buat field review", "review", "create", ""),
    ("review.update", "Ubah field review", "review", "update", ""),
    ("review.delete", "Hapus field review", "review", "delete", ""),
    ("review.close_finding", "Tutup temuan", "review", "close_finding", ""),
    # --- payment ---
    ("payment.read", "Lihat termin", "payment", "read", ""),
    ("payment.create", "Buat termin", "payment", "create", ""),
    ("payment.update", "Ubah termin", "payment", "update", ""),
    ("payment.delete", "Hapus termin DRAFT", "payment", "delete", ""),
    ("payment.submit", "Submit termin", "payment", "submit", ""),
    ("payment.verify", "Verifikasi termin", "payment", "verify", ""),
    ("payment.pay", "Tandai termin PAID", "payment", "pay", ""),
    ("payment.reject", "Reject termin", "payment", "reject", ""),
    # --- notify ---
    ("notify.read", "Lihat aturan notifikasi", "notify", "read", ""),
    ("notify.update", "Ubah aturan notifikasi", "notify", "update", ""),
]


# Role bawaan (Bagian 2 CLAUDE.md). is_system=True -> tidak bisa dihapus.
ROLES: dict[str, dict] = {
    "superadmin": {
        "name": "Superadmin",
        "description": "God-mode. Akses penuh.",
        "permissions": "*",  # semua
    },
    "admin_pusat": {
        "name": "Admin Pusat",
        "description": "Operator pusat. Kelola kontrak, master, laporan, termin.",
        "permissions": [
            "company.*", "ppk.*", "master.*",
            "contract.*", "location.*", "facility.*",
            "boq.*", "vo.*", "mc.*", "addendum.*",
            "report_daily.*", "report_weekly.*",
            "review.read",
            "payment.*",
            "notify.read", "audit.read",
        ],
    },
    "ppk": {
        "name": "PPK",
        "description": "Pejabat Pembuat Komitmen. Pemilik kontrak.",
        "permissions": [
            "company.read", "ppk.read", "master.read",
            "contract.read", "contract.create", "contract.update",
            "contract.activate", "contract.complete",
            "location.*", "facility.*",
            "boq.read", "boq.update", "boq.approve",
            "vo.read", "vo.approve", "vo.reject",
            "mc.read",
            "addendum.read", "addendum.create", "addendum.update", "addendum.sign",
            "report_daily.read", "report_weekly.read", "report_weekly.lock",
            "review.read",
            "payment.read", "payment.create", "payment.update",
            "payment.submit", "payment.verify", "payment.pay", "payment.reject",
            "notify.read",
        ],
    },
    "manager": {
        "name": "Manager / Koordinator",
        "description": "Monitor multi-kontrak. Read-only luas.",
        "permissions": [
            "company.read", "ppk.read", "master.read",
            "contract.read", "location.read", "facility.read",
            "boq.read", "vo.read", "mc.read", "addendum.read",
            "report_daily.read", "report_weekly.read",
            "review.read", "payment.read", "notify.read",
        ],
    },
    "konsultan": {
        "name": "Konsultan MK",
        "description": "Pengawas lapangan. Input laporan, review teknis VO.",
        "permissions": [
            "contract.read", "location.read", "facility.read",
            "boq.read",
            "vo.read", "vo.create", "vo.update", "vo.submit",
            "mc.read", "mc.create", "mc.update",
            "addendum.read",
            "report_daily.*", "report_weekly.*",
            "review.read",
            "payment.read",
        ],
    },
    "kontraktor": {
        "name": "Kontraktor",
        "description": "Pelaksana fisik. Read-only kontrak miliknya.",
        "permissions": [
            "contract.read", "location.read", "facility.read",
            "boq.read", "vo.read", "mc.read", "addendum.read",
            "report_daily.read", "report_weekly.read",
            "review.read", "payment.read",
        ],
    },
    "itjen": {
        "name": "Itjen (Inspektorat Jenderal)",
        "description": "Inspektur internal. Buat field review.",
        "permissions": [
            "contract.read", "location.read", "facility.read",
            "boq.read", "vo.read", "mc.read", "addendum.read",
            "report_daily.read", "report_weekly.read",
            "review.*", "payment.read", "audit.read",
        ],
    },
    "viewer": {
        "name": "Viewer",
        "description": "Pengamat pasif. Read-only.",
        "permissions": [
            "contract.read", "location.read", "facility.read",
            "boq.read", "vo.read", "mc.read", "addendum.read",
            "report_daily.read", "report_weekly.read",
            "review.read", "payment.read",
        ],
    },
}


# Menu tree. Tree definisi sederhana — anak diidentifikasi via parent_code.
MENUS: list[dict] = [
    {"code": "dashboard", "label": "Dashboard", "icon": "layout-dashboard", "route": "/dashboard", "order": 10},
    {"code": "peta", "label": "Peta", "icon": "map", "route": "/peta", "order": 15},
    {"code": "galeri", "label": "Galeri Foto", "icon": "image", "route": "/galeri", "order": 20},
    {"code": "kontrak", "label": "Kontrak", "icon": "file-text", "route": "/kontrak", "order": 30},
    {"code": "notifikasi", "label": "Notifikasi", "icon": "bell", "route": "/notifikasi", "order": 80},
    {"code": "pengaturan", "label": "Pengaturan", "icon": "settings", "route": "/pengaturan", "order": 90},
    {"code": "pengaturan_user", "label": "User", "icon": "users",
     "route": "/pengaturan/users", "order": 1, "parent_code": "pengaturan"},
    {"code": "pengaturan_role", "label": "Role & Permission", "icon": "shield",
     "route": "/pengaturan/roles", "order": 2, "parent_code": "pengaturan"},
    {"code": "pengaturan_menu", "label": "Menu", "icon": "list-tree",
     "route": "/pengaturan/menus", "order": 3, "parent_code": "pengaturan"},
    {"code": "pengaturan_master_company", "label": "Perusahaan", "icon": "building",
     "route": "/pengaturan/master/companies", "order": 4, "parent_code": "pengaturan"},
    {"code": "pengaturan_master_ppk", "label": "PPK", "icon": "user-cog",
     "route": "/pengaturan/master/ppks", "order": 5, "parent_code": "pengaturan"},
    {"code": "pengaturan_master_facility", "label": "Master Fasilitas", "icon": "package",
     "route": "/pengaturan/master/facilities", "order": 6, "parent_code": "pengaturan"},
    {"code": "pengaturan_master_workcode", "label": "Master Kode Pekerjaan", "icon": "tag",
     "route": "/pengaturan/master/work-codes", "order": 7, "parent_code": "pengaturan"},
    {"code": "pengaturan_audit", "label": "Audit Log", "icon": "history",
     "route": "/pengaturan/audit", "order": 8, "parent_code": "pengaturan"},
    {"code": "pengaturan_godmode", "label": "God Mode", "icon": "alert-triangle",
     "route": "/pengaturan/godmode", "order": 99, "parent_code": "pengaturan"},
]

# Menu yang dilihat per role
ROLE_MENUS: dict[str, list[str]] = {
    "superadmin": [m["code"] for m in MENUS],
    "admin_pusat": [
        "dashboard", "peta", "galeri", "kontrak", "notifikasi", "pengaturan",
        "pengaturan_master_company", "pengaturan_master_ppk",
        "pengaturan_master_facility", "pengaturan_master_workcode",
    ],
    "ppk": ["dashboard", "peta", "galeri", "kontrak", "notifikasi"],
    "manager": ["dashboard", "peta", "galeri", "kontrak", "notifikasi"],
    "konsultan": ["dashboard", "kontrak", "galeri", "notifikasi"],
    "kontraktor": ["dashboard", "kontrak", "galeri", "notifikasi"],
    "itjen": ["dashboard", "peta", "galeri", "kontrak", "notifikasi", "pengaturan", "pengaturan_audit"],
    "viewer": ["dashboard", "kontrak", "galeri"],
}


def _expand_perms(patterns: list[str] | str, all_codes: set[str]) -> set[str]:
    if patterns == "*":
        return set(all_codes)
    out: set[str] = set()
    for pat in patterns:
        if pat.endswith(".*"):
            module = pat[:-2]
            out.update({c for c in all_codes if c.startswith(module + ".")})
        else:
            if pat in all_codes:
                out.add(pat)
    return out


class Command(BaseCommand):
    help = "Seed initial data: permissions, roles, menus."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding permissions..."))
        for code, name, module, action, desc in PERMISSIONS:
            Permission.objects.update_or_create(
                code=code,
                defaults={"name": name, "module": module, "action": action, "description": desc},
            )
        all_codes = set(Permission.objects.values_list("code", flat=True))
        self.stdout.write(f"  -> {len(all_codes)} permission entries.")

        self.stdout.write(self.style.MIGRATE_HEADING("Seeding menus..."))
        # 2 pass: parent dulu, anak kemudian
        for m in [x for x in MENUS if "parent_code" not in x]:
            Menu.objects.update_or_create(
                code=m["code"],
                defaults={"label": m["label"], "icon": m.get("icon", ""),
                          "route": m.get("route", ""), "order": m.get("order", 0),
                          "parent": None, "is_active": True},
            )
        for m in [x for x in MENUS if "parent_code" in x]:
            parent = Menu.objects.get(code=m["parent_code"])
            Menu.objects.update_or_create(
                code=m["code"],
                defaults={"label": m["label"], "icon": m.get("icon", ""),
                          "route": m.get("route", ""), "order": m.get("order", 0),
                          "parent": parent, "is_active": True},
            )
        self.stdout.write(f"  -> {Menu.objects.count()} menu entries.")

        self.stdout.write(self.style.MIGRATE_HEADING("Seeding roles..."))
        for code, cfg in ROLES.items():
            role, _ = Role.objects.update_or_create(
                code=code,
                defaults={"name": cfg["name"], "description": cfg["description"],
                          "is_system": True},
            )
            perm_codes = _expand_perms(cfg["permissions"], all_codes)
            perms = list(Permission.objects.filter(code__in=perm_codes))
            role.permissions.set(perms)

            menu_codes = ROLE_MENUS.get(code, [])
            menus = list(Menu.objects.filter(code__in=menu_codes))
            role.menus.set(menus)

            self.stdout.write(f"  -> role '{code}': {len(perms)} perms, {len(menus)} menus.")

        self.stdout.write(self.style.SUCCESS("Seed selesai."))
