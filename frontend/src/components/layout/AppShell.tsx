"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard, Map, Image as ImageIcon, FileText, Bell, Settings,
  Users, Shield, ListTree, Building, UserCog, Package, Tag, History,
  AlertTriangle, LogOut, Sun, Moon, Menu as MenuIcon, X,
} from "lucide-react";
import { toast } from "sonner";

import { useAuthStore, type MenuNode } from "@/lib/auth/store";
import { fetchMe, logout } from "@/lib/auth/actions";
import { cn } from "@/lib/utils";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  "layout-dashboard": LayoutDashboard,
  "map": Map,
  "image": ImageIcon,
  "file-text": FileText,
  "bell": Bell,
  "settings": Settings,
  "users": Users,
  "shield": Shield,
  "list-tree": ListTree,
  "building": Building,
  "user-cog": UserCog,
  "package": Package,
  "tag": Tag,
  "history": History,
  "alert-triangle": AlertTriangle,
};

function Icon({ name, className }: { name?: string; className?: string }) {
  const C = name ? ICONS[name] : null;
  if (!C) return null;
  return <C className={className} />;
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { me, hydrated, access } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [dark, setDark] = useState(false);

  // Initial hydration: fetch /me jika sudah ada token tapi belum punya data me.
  useEffect(() => {
    if (!hydrated) return;
    if (!access) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    if (!me) {
      fetchMe().catch(() => router.replace("/login"));
    } else if (me.must_change_password && pathname !== "/ganti-password") {
      router.replace("/ganti-password");
    }
  }, [hydrated, access, me, router, pathname]);

  // Theme toggle
  useEffect(() => {
    const stored = localStorage.getItem("rasmara-theme");
    const isDark = stored === "dark"
      || (stored === null && window.matchMedia("(prefers-color-scheme: dark)").matches);
    setDark(isDark);
    document.documentElement.classList.toggle("dark", isDark);
  }, []);

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("rasmara-theme", next ? "dark" : "light");
  }

  async function onLogout() {
    await logout();
    toast.success("Anda telah keluar.");
    router.replace("/login");
  }

  if (!hydrated || !me) {
    return (
      <div className="min-h-screen grid place-items-center text-muted-fg text-sm">
        Memuat...
      </div>
    );
  }

  const menus = me.menu_tree;

  return (
    <div className="min-h-screen flex bg-background">
      {/* Sidebar */}
      <aside
        className={cn(
          "fixed lg:sticky top-0 z-40 h-screen border-r bg-card transition-all flex flex-col",
          collapsed ? "w-[68px]" : "w-64",
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
        )}
      >
        <div className="h-14 flex items-center justify-between px-3 border-b">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="size-8 rounded-lg bg-primary text-primary-fg grid place-items-center font-bold text-sm">
              R
            </div>
            {!collapsed && <span className="font-semibold">RASMARA</span>}
          </Link>
          <button
            className="lg:hidden btn-ghost p-1.5"
            onClick={() => setMobileOpen(false)}
            aria-label="Tutup menu"
          >
            <X className="size-4" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto py-3">
          <ul className="space-y-0.5 px-2">
            {menus.map((m) => (
              <SidebarItem key={m.id} item={m} collapsed={collapsed} pathname={pathname} />
            ))}
          </ul>
        </nav>

        <div className="border-t p-2 space-y-1">
          <button
            onClick={toggleTheme}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm hover:bg-muted"
            title={dark ? "Mode terang" : "Mode gelap"}
          >
            {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
            {!collapsed && <span>{dark ? "Mode terang" : "Mode gelap"}</span>}
          </button>
          <button
            onClick={onLogout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm hover:bg-danger/10 text-danger"
          >
            <LogOut className="size-4" />
            {!collapsed && <span>Keluar</span>}
          </button>
        </div>
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={() => setMobileOpen(false)} />
      )}

      {/* Main */}
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="h-14 sticky top-0 z-20 border-b bg-card flex items-center justify-between px-4 gap-4">
          <div className="flex items-center gap-2">
            <button
              className="lg:hidden btn-ghost p-1.5"
              onClick={() => setMobileOpen(true)}
              aria-label="Buka menu"
            >
              <MenuIcon className="size-5" />
            </button>
            <button
              className="hidden lg:block btn-ghost p-1.5"
              onClick={() => setCollapsed((v) => !v)}
              aria-label="Lipat sidebar"
            >
              <MenuIcon className="size-5" />
            </button>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-fg hidden md:block">
              {me.role_name || "Pengguna"}
            </span>
            <Link href="/profil" className="size-8 rounded-full bg-primary/10 text-primary grid place-items-center text-sm font-medium" title={me.full_name}>
              {me.full_name.slice(0, 2).toUpperCase()}
            </Link>
          </div>
        </header>

        <main className="flex-1 p-4 md:p-6 overflow-x-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

function SidebarItem({
  item, collapsed, pathname, depth = 0,
}: {
  item: MenuNode; collapsed: boolean; pathname: string; depth?: number;
}) {
  const [open, setOpen] = useState(true);
  const hasChildren = (item.children?.length ?? 0) > 0;
  const active = item.route && (pathname === item.route || pathname.startsWith(item.route + "/"));

  if (hasChildren) {
    return (
      <li>
        <button
          onClick={() => setOpen((v) => !v)}
          className={cn(
            "w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm hover:bg-muted",
            active && "bg-muted font-medium",
          )}
        >
          <Icon name={item.icon} className="size-4 shrink-0" />
          {!collapsed && (
            <>
              <span className="flex-1 text-left truncate">{item.label}</span>
              <span className="text-xs text-muted-fg">{open ? "−" : "+"}</span>
            </>
          )}
        </button>
        {open && !collapsed && (
          <ul className="ml-4 mt-0.5 border-l pl-2 space-y-0.5">
            {item.children!.map((c) => (
              <SidebarItem key={c.id} item={c} collapsed={false} pathname={pathname} depth={depth + 1} />
            ))}
          </ul>
        )}
      </li>
    );
  }

  return (
    <li>
      <Link
        href={item.route || "#"}
        className={cn(
          "flex items-center gap-2 px-3 py-2 rounded-lg text-sm hover:bg-muted",
          active && "bg-primary/10 text-primary font-medium",
        )}
        title={collapsed ? item.label : undefined}
      >
        <Icon name={item.icon} className="size-4 shrink-0" />
        {!collapsed && <span className="truncate">{item.label}</span>}
      </Link>
    </li>
  );
}
