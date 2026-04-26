import AppShell from "@/components/layout/AppShell";

// Halaman di belakang AppShell butuh auth state (localStorage) — skip prerender.
export const dynamic = "force-dynamic";

export default function Layout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
