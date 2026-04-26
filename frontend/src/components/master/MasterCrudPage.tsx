"use client";

/**
 * MasterCrudPage — kerangka generic untuk halaman master data.
 * Menyediakan: search, filter dropdown, pagination, table, modal create/edit, delete confirm.
 */
import { ReactNode, useState } from "react";
import useSWR from "swr";
import { Plus, RefreshCw, Search, Edit2, Trash2, X } from "lucide-react";
import { toast } from "sonner";

import { api, ApiError, swrFetcher } from "@/lib/api/client";
import { useAuthStore } from "@/lib/auth/store";

type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };

export type Column<T> = {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  width?: string;
};

export type FilterOption = { value: string; label: string };

type Props<T extends { id: string }> = {
  title: string;
  resourceUrl: string;        // mis. "/companies/"
  permRead: string;
  permCreate: string;
  permUpdate: string;
  permDelete: string;
  columns: Column<T>[];
  searchPlaceholder?: string;
  /** dropdown filter tambahan: ?<key>=<value> */
  filters?: Array<{
    key: string;
    label: string;
    options: FilterOption[];
  }>;
  /** Render form dalam modal. setForm util harus digunakan utk mutasi state. */
  renderForm: (state: {
    form: any;
    setForm: (f: any) => void;
    editing: T | null;
  }) => ReactNode;
  /** Validasi & transform sebelum POST/PATCH (return body atau throw) */
  prepareSubmit?: (form: any, editing: T | null) => any;
  /** Initial form ketika create */
  initialForm: any;
  /** Bila ada response special (mis. initial_password), tampilkan toast */
  onCreated?: (created: any) => void;
  onUpdated?: (updated: any) => void;
};

export default function MasterCrudPage<T extends { id: string }>(props: Props<T>) {
  const { hasPerm } = useAuthStore();
  const [search, setSearch] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});

  const params = new URLSearchParams();
  if (search) params.set("search", search);
  Object.entries(filterValues).forEach(([k, v]) => v && params.set(k, v));

  const url = `${props.resourceUrl}?${params.toString()}`;
  const { data, isLoading, mutate } = useSWR<Paginated<T>>(url, swrFetcher);

  const [editing, setEditing] = useState<T | null>(null);
  const [showForm, setShowForm] = useState(false);

  const canCreate = hasPerm(props.permCreate);
  const canUpdate = hasPerm(props.permUpdate);
  const canDelete = hasPerm(props.permDelete);

  function openCreate() {
    setEditing(null);
    setShowForm(true);
  }

  function openEdit(row: T) {
    setEditing(row);
    setShowForm(true);
  }

  async function onDelete(row: T) {
    if (!confirm(`Hapus "${(row as any).name || (row as any).code || row.id}"?`)) return;
    try {
      await api(`${props.resourceUrl}${row.id}/`, { method: "DELETE" });
      toast.success("Data terhapus.");
      mutate();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h1 className="text-2xl font-bold">{props.title}</h1>
        <div className="flex items-center gap-2">
          <button onClick={() => mutate()} className="btn-ghost" title="Refresh">
            <RefreshCw className="size-4" />
          </button>
          {canCreate && (
            <button onClick={openCreate} className="btn-primary">
              <Plus className="size-4 mr-1" /> Tambah
            </button>
          )}
        </div>
      </div>

      <div className="card p-4">
        <div className="flex gap-2 flex-wrap mb-4">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-fg" />
            <input
              className="input pl-9"
              placeholder={props.searchPlaceholder || "Cari..."}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          {props.filters?.map((f) => (
            <select
              key={f.key}
              className="input max-w-[200px]"
              value={filterValues[f.key] || ""}
              onChange={(e) =>
                setFilterValues({ ...filterValues, [f.key]: e.target.value })
              }
            >
              <option value="">{f.label} (semua)</option>
              {f.options.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          ))}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b text-muted-fg">
                {props.columns.map((c) => (
                  <th key={c.key} className="py-2 pr-4" style={c.width ? { width: c.width } : {}}>
                    {c.header}
                  </th>
                ))}
                {(canUpdate || canDelete) && <th className="py-2 pr-2 w-32">Aksi</th>}
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={props.columns.length + 1} className="py-6 text-center text-muted-fg">Memuat...</td></tr>
              )}
              {data?.results?.length === 0 && (
                <tr><td colSpan={props.columns.length + 1} className="py-6 text-center text-muted-fg">Tidak ada data.</td></tr>
              )}
              {data?.results?.map((row) => (
                <tr key={row.id} className="border-b hover:bg-muted/30">
                  {props.columns.map((c) => (
                    <td key={c.key} className="py-2 pr-4">
                      {c.render ? c.render(row) : ((row as any)[c.key] ?? "—")}
                    </td>
                  ))}
                  {(canUpdate || canDelete) && (
                    <td className="py-2 pr-2 space-x-2">
                      {canUpdate && (
                        <button onClick={() => openEdit(row)}
                                className="text-primary hover:underline text-xs inline-flex items-center gap-1">
                          <Edit2 className="size-3" /> Edit
                        </button>
                      )}
                      {canDelete && (
                        <button onClick={() => onDelete(row)}
                                className="text-danger hover:underline text-xs inline-flex items-center gap-1">
                          <Trash2 className="size-3" /> Hapus
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {data && (
          <div className="mt-3 text-xs text-muted-fg">
            Total: {data.count} entri.
          </div>
        )}
      </div>

      {showForm && (
        <FormModal
          editing={editing}
          initialForm={props.initialForm}
          renderForm={props.renderForm}
          prepareSubmit={props.prepareSubmit}
          resourceUrl={props.resourceUrl}
          onClose={() => setShowForm(false)}
          onSaved={(created) => {
            setShowForm(false);
            mutate();
            if (editing) {
              props.onUpdated?.(created);
            } else {
              props.onCreated?.(created);
            }
          }}
        />
      )}
    </div>
  );
}

function FormModal<T extends { id: string }>({
  editing, initialForm, renderForm, prepareSubmit, resourceUrl, onClose, onSaved,
}: {
  editing: T | null;
  initialForm: any;
  renderForm: Props<T>["renderForm"];
  prepareSubmit?: Props<T>["prepareSubmit"];
  resourceUrl: string;
  onClose: () => void;
  onSaved: (created: any) => void;
}) {
  const [form, setForm] = useState<any>(editing ? { ...initialForm, ...editing } : initialForm);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const body = prepareSubmit ? prepareSubmit(form, editing) : form;
      let res: any;
      if (editing) {
        res = await api(`${resourceUrl}${editing.id}/`, { method: "PATCH", body });
        toast.success("Data tersimpan.");
      } else {
        res = await api(resourceUrl, { method: "POST", body });
        toast.success("Data dibuat.");
      }
      onSaved(res);
    } catch (err) {
      if (err instanceof ApiError) {
        const detail = err.details ? "\n" + JSON.stringify(err.details, null, 2) : "";
        toast.error(`${err.message}${detail}`);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4">
      <form onSubmit={onSubmit}
            className="card p-6 w-full max-w-xl max-h-[90vh] overflow-y-auto space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">{editing ? "Edit" : "Tambah Baru"}</h2>
          <button type="button" onClick={onClose} className="btn-ghost p-1.5" aria-label="Tutup">
            <X className="size-4" />
          </button>
        </div>
        {renderForm({ form, setForm, editing })}
        <div className="flex gap-2 pt-2">
          <button type="button" onClick={onClose} className="btn-secondary flex-1" disabled={submitting}>
            Batal
          </button>
          <button type="submit" className="btn-primary flex-1" disabled={submitting}>
            {submitting ? "Menyimpan..." : "Simpan"}
          </button>
        </div>
      </form>
    </div>
  );
}
