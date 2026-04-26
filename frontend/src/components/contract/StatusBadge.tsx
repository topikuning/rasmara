import { cn } from "@/lib/utils";

const STYLE: Record<string, string> = {
  DRAFT: "bg-muted text-muted-fg",
  ACTIVE: "bg-success/10 text-success",
  ON_HOLD: "bg-warning/10 text-warning",
  COMPLETED: "bg-primary/10 text-primary",
  TERMINATED: "bg-danger/10 text-danger",
};

const LABEL: Record<string, string> = {
  DRAFT: "Draft",
  ACTIVE: "Aktif",
  ON_HOLD: "Pause",
  COMPLETED: "Selesai",
  TERMINATED: "Dihentikan",
};

export function ContractStatusBadge({ status, className }: { status: string; className?: string }) {
  return (
    <span className={cn(
      "inline-block px-2 py-0.5 rounded text-xs font-medium",
      STYLE[status] || "bg-muted text-muted-fg",
      className,
    )}>
      {LABEL[status] || status}
    </span>
  );
}
