/**
 * Halaman utama (landing) - publik.
 * Untuk akses awal via IP di port 80, halaman ini yang tampil pertama.
 */
import Link from "next/link";
import { ShieldCheck, BarChart3, FileSpreadsheet, Map, Bell } from "lucide-react";

export default function HomePage() {
  return (
    <main className="min-h-screen">
      {/* Hero */}
      <section className="border-b">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <div className="flex items-center gap-2 text-sm text-muted-fg mb-6">
            <span className="inline-block size-2 rounded-full bg-success" />
            Sistem aktif
          </div>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight">
            RASMARA
          </h1>
          <p className="mt-2 text-lg md:text-xl text-muted-fg max-w-3xl">
            Real-time Analytics System for Monitoring, Allocation, Reporting & Accountability.
          </p>
          <p className="mt-6 max-w-3xl text-base md:text-lg leading-relaxed">
            Sistem monitoring pelaksanaan kontrak konstruksi infrastruktur — khususnya
            proyek pemerintahan, dengan compliance terhadap Perpres 16/2018 ps. 54
            (perubahan kontrak via Addendum/CCO).
          </p>
          <div className="mt-10 flex flex-wrap gap-3">
            <Link href="/login" className="btn-primary">
              Masuk ke Sistem
            </Link>
            <a href="/api/v1/health/" className="btn-secondary" target="_blank" rel="noreferrer">
              Status API
            </a>
          </div>
        </div>
      </section>

      {/* Fitur ringkas */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <h2 className="text-2xl font-semibold mb-8">Cakupan Sistem</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <Feature
            icon={<FileSpreadsheet className="size-5" />}
            title="Kontrak & BOQ"
            desc="Kelola kontrak, lokasi, fasilitas, BOQ hirarkis 4 level dengan versioning V0/V1/…"
          />
          <Feature
            icon={<BarChart3 className="size-5" />}
            title="Pelaporan Progres"
            desc="Laporan harian & mingguan, kalkulasi otomatis SPI, deviasi, kurva-S realtime."
          />
          <Feature
            icon={<ShieldCheck className="size-5" />}
            title="Variation Order & Addendum"
            desc="Siklus VO formal, threshold KPA 10%, auto-clone revisi BOQ saat addendum di-sign."
          />
          <Feature
            icon={<Map className="size-5" />}
            title="Dashboard Eksekutif"
            desc="Peta interaktif lokasi proyek, marker status, galeri foto, kurva-S multi-kontrak."
          />
          <Feature
            icon={<Bell className="size-5" />}
            title="Notifikasi & Early Warning"
            desc="Deteksi laporan telat, deviasi kritis, termin jatuh tempo via WhatsApp/Email/In-App."
          />
          <Feature
            icon={<ShieldCheck className="size-5" />}
            title="Audit & Akuntabilitas"
            desc="Audit log lengkap diff before/after, RBAC dinamis, anchor BOQ pada termin pembayaran."
          />
        </div>
      </section>

      <footer className="border-t">
        <div className="mx-auto max-w-6xl px-6 py-8 text-sm text-muted-fg flex flex-wrap items-center justify-between gap-4">
          <span>&copy; {new Date().getFullYear()} RASMARA — Sistem Internal Pemantauan Kontrak.</span>
          <span className="text-xs">Modul aktif: Fondasi (Auth, RBAC, Audit) v0.1.0</span>
        </div>
      </footer>
    </main>
  );
}

function Feature({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="card p-5">
      <div className="size-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center mb-3">
        {icon}
      </div>
      <h3 className="font-semibold mb-1">{title}</h3>
      <p className="text-sm text-muted-fg">{desc}</p>
    </div>
  );
}
