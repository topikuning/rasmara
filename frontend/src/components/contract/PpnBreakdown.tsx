import { formatRupiahFull } from "@/lib/format/rupiah";

/**
 * Breakdown PPN eksplisit (Bagian 7 & 13.1 CLAUDE.md):
 *   BOQ Rp X + PPN Rp Y (Z%) = Nilai Kontrak Rp Total
 * Hindari notasi ambigu seperti "BOQ × (1+11%)".
 */
export function PpnBreakdown({
  boqValue, ppnPct, contractValue, compact = false,
}: {
  boqValue: number | string;
  ppnPct: number | string;
  contractValue: number | string;
  compact?: boolean;
}) {
  const boq = Number(boqValue);
  const pct = Number(ppnPct);
  const contract = Number(contractValue);
  const ppn = boq * (pct / 100);

  if (compact) {
    return (
      <div className="text-sm">
        <span className="font-medium">{formatRupiahFull(contract)}</span>
        <span className="text-muted-fg"> (BOQ + PPN {pct}%)</span>
      </div>
    );
  }

  return (
    <div className="flex items-baseline flex-wrap gap-x-2 gap-y-1 text-sm">
      <span className="text-muted-fg">BOQ</span>
      <span className="font-mono">{formatRupiahFull(boq)}</span>
      <span className="text-muted-fg">+ PPN</span>
      <span className="font-mono">{formatRupiahFull(ppn)}</span>
      <span className="text-muted-fg">({pct}%)</span>
      <span className="text-muted-fg">=</span>
      <span className="font-mono font-semibold">{formatRupiahFull(contract)}</span>
    </div>
  );
}
