import { format, parseISO } from "date-fns";
import { id } from "date-fns/locale";

export function formatTanggalID(date: string | Date | null | undefined): string {
  if (!date) return "-";
  const d = typeof date === "string" ? parseISO(date) : date;
  return format(d, "d MMMM yyyy", { locale: id });
}

export function formatTanggalSingkat(date: string | Date | null | undefined): string {
  if (!date) return "-";
  const d = typeof date === "string" ? parseISO(date) : date;
  return format(d, "d MMM yyyy", { locale: id });
}

export function formatTanggalJam(date: string | Date | null | undefined): string {
  if (!date) return "-";
  const d = typeof date === "string" ? parseISO(date) : date;
  return format(d, "d MMM yyyy HH:mm", { locale: id });
}
