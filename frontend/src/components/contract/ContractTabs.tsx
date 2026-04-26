"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const TABS = [
  { key: "ringkasan", label: "Ringkasan" },
  { key: "lokasi", label: "Lokasi & Fasilitas" },
  { key: "boq", label: "BOQ" },
  { key: "mc", label: "MC (Field Obs)" },
  { key: "vo", label: "VO" },
  { key: "addendum", label: "Addendum" },
  { key: "laporan-mingguan", label: "Laporan" },
  { key: "termin", label: "Termin" },
  { key: "field-review", label: "Field Review" },
  { key: "galeri", label: "Galeri" },
  { key: "timeline", label: "Timeline" },
];

export function ContractTabs({ contractId }: { contractId: string }) {
  const pathname = usePathname();
  return (
    <div className="border-b">
      <div className="flex flex-wrap gap-1 -mb-px overflow-x-auto">
        {TABS.map((t) => {
          const href = `/kontrak/${contractId}/${t.key}`;
          const active = pathname.startsWith(href);
          return (
            <Link
              key={t.key}
              href={href}
              className={cn(
                "px-4 py-2.5 text-sm border-b-2 transition-colors whitespace-nowrap",
                active
                  ? "border-primary text-primary font-medium"
                  : "border-transparent text-muted-fg hover:text-fg",
              )}
            >
              {t.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
