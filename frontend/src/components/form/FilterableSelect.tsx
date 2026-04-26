"use client";

/**
 * FilterableSelect — dropdown searchable server-side dengan debounce.
 * Wajib dipakai di SEMUA dropdown (Bagian 13.7 CLAUDE.md).
 *
 * Pemakaian:
 *   <FilterableSelect
 *     value={form.company_id}
 *     onChange={(id, item) => setForm({...form, company_id: id})}
 *     fetchUrl="/companies/lookup/"   // backend lookup endpoint
 *     getLabel={(c) => `${c.code} - ${c.name}`}
 *     placeholder="Pilih perusahaan..."
 *   />
 */
import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, Loader2, Search, X } from "lucide-react";

import { api } from "@/lib/api/client";
import { cn } from "@/lib/utils";

type Item = { id: string; [k: string]: any };

type Props<T extends Item> = {
  value: string | null | undefined;
  onChange: (id: string | null, item: T | null) => void;
  fetchUrl: string;             // mis. "/companies/lookup/"
  getLabel: (item: T) => string;
  getSubLabel?: (item: T) => string | null;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  className?: string;
  /** Initial item kalau value ada tapi label belum diketahui (mis. dari edit) */
  initialItem?: T | null;
  searchParam?: string;        // default 'search'
  debounceMs?: number;
};

export default function FilterableSelect<T extends Item>({
  value, onChange, fetchUrl, getLabel, getSubLabel,
  placeholder = "Pilih...", disabled, required, className,
  initialItem, searchParam = "search", debounceMs = 250,
}: Props<T>) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedItem, setSelectedItem] = useState<T | null>(initialItem ?? null);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Saat value berubah dari luar (mis. reset form), sinkron selectedItem
  useEffect(() => {
    if (!value) {
      setSelectedItem(null);
      return;
    }
    if (selectedItem?.id === value) return;
    if (initialItem?.id === value) {
      setSelectedItem(initialItem);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  // Debounced fetch
  useEffect(() => {
    if (!open) return;
    let cancel = false;
    setLoading(true);
    const handle = setTimeout(async () => {
      try {
        const sep = fetchUrl.includes("?") ? "&" : "?";
        const url = `${fetchUrl}${sep}${searchParam}=${encodeURIComponent(query)}`;
        const data = await api<T[] | { results: T[] }>(url);
        if (cancel) return;
        const list = Array.isArray(data) ? data : (data.results ?? []);
        setItems(list);
      } catch {
        if (!cancel) setItems([]);
      } finally {
        if (!cancel) setLoading(false);
      }
    }, debounceMs);
    return () => { cancel = true; clearTimeout(handle); };
  }, [open, query, fetchUrl, searchParam, debounceMs]);

  // Click outside to close
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  function pick(item: T | null) {
    setSelectedItem(item);
    onChange(item?.id ?? null, item);
    setOpen(false);
    setQuery("");
  }

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      {/* trigger */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => { setOpen((v) => !v); setTimeout(() => inputRef.current?.focus(), 50); }}
        className={cn(
          "input flex items-center justify-between gap-2 cursor-default",
          disabled && "opacity-50 cursor-not-allowed",
        )}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className={cn("truncate text-left", !selectedItem && "text-muted-fg")}>
          {selectedItem ? getLabel(selectedItem) : placeholder}
        </span>
        <span className="flex items-center gap-1 shrink-0">
          {selectedItem && !required && !disabled && (
            <span
              role="button"
              tabIndex={0}
              onClick={(e) => { e.stopPropagation(); pick(null); }}
              className="p-0.5 hover:text-danger"
              aria-label="Bersihkan pilihan"
            >
              <X className="size-3.5" />
            </span>
          )}
          <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} />
        </span>
      </button>

      {/* dropdown panel */}
      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-lg border bg-card shadow-lg max-h-72 overflow-hidden flex flex-col">
          <div className="p-2 border-b">
            <div className="relative">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 size-4 text-muted-fg" />
              <input
                ref={inputRef}
                className="input pl-8 py-1.5 text-sm"
                placeholder="Ketik untuk mencari..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Escape") setOpen(false);
                  if (e.key === "Enter" && items[0]) {
                    e.preventDefault();
                    pick(items[0]);
                  }
                }}
              />
              {loading && (
                <Loader2 className="absolute right-2 top-1/2 -translate-y-1/2 size-4 animate-spin text-muted-fg" />
              )}
            </div>
          </div>
          <ul className="overflow-y-auto flex-1">
            {!loading && items.length === 0 && (
              <li className="px-3 py-4 text-center text-sm text-muted-fg">
                Tidak ada hasil.
              </li>
            )}
            {items.map((it) => (
              <li key={it.id}>
                <button
                  type="button"
                  onClick={() => pick(it)}
                  className="w-full text-left px-3 py-2 hover:bg-muted flex items-center gap-2"
                >
                  <span className="size-4 shrink-0">
                    {selectedItem?.id === it.id && <Check className="size-4 text-primary" />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm truncate">{getLabel(it)}</div>
                    {getSubLabel && (
                      <div className="text-xs text-muted-fg truncate">{getSubLabel(it)}</div>
                    )}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
