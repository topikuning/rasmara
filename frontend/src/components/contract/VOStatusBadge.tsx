import { cn } from "@/lib/utils";

const STYLE: Record<string, string> = {
  DRAFT: "bg-muted text-muted-fg",
  UNDER_REVIEW: "bg-warning/10 text-warning",
  APPROVED: "bg-primary/10 text-primary",
  REJECTED: "bg-danger/10 text-danger",
  BUNDLED: "bg-success/10 text-success",
};

const LABEL: Record<string, string> = {
  DRAFT: "Draft",
  UNDER_REVIEW: "Direview",
  APPROVED: "Disetujui",
  REJECTED: "Ditolak",
  BUNDLED: "Bundled",
};

export function VOStatusBadge({ status, className }: { status: string; className?: string }) {
  return (
    <span className={cn(
      "inline-block px-2 py-0.5 rounded text-xs font-medium",
      STYLE[status] || "bg-muted",
      className,
    )}>
      {LABEL[status] || status}
    </span>
  );
}

const ADD_STYLE: Record<string, string> = {
  DRAFT: "bg-muted text-muted-fg",
  SIGNED: "bg-success/10 text-success",
};
const ADD_LABEL: Record<string, string> = {
  DRAFT: "Draft",
  SIGNED: "Sudah TTD",
};

export function AddendumStatusBadge({ status, className }: { status: string; className?: string }) {
  return (
    <span className={cn(
      "inline-block px-2 py-0.5 rounded text-xs font-medium",
      ADD_STYLE[status] || "bg-muted",
      className,
    )}>
      {ADD_LABEL[status] || status}
    </span>
  );
}
