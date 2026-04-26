"""Django admin minimal untuk debug. UI utama tetap di Next.js."""
from django.contrib import admin

from .models import AuditLog, Menu, Permission, Role, RoleMenu, RolePermission, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "full_name", "email", "role", "is_active", "is_superuser",
                    "must_change_password", "auto_provisioned", "last_login")
    search_fields = ("username", "full_name", "email")
    list_filter = ("role", "is_active", "is_superuser")
    readonly_fields = ("last_login", "created_at", "updated_at")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_system")
    search_fields = ("code", "name")


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "module", "action")
    search_fields = ("code", "name", "module", "action")
    list_filter = ("module",)


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "route", "parent", "order", "is_active")
    search_fields = ("code", "label", "route")


admin.site.register(RolePermission)
admin.site.register(RoleMenu)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("ts", "user", "action", "entity_type", "entity_repr",
                    "ip_address", "godmode_bypass")
    list_filter = ("action", "entity_type", "godmode_bypass")
    search_fields = ("entity_repr", "entity_type", "user__username")
    readonly_fields = [f.name for f in AuditLog._meta.fields]
    ordering = ("-ts",)
