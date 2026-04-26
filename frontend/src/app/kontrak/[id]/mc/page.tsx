"use client";

import { use, useState } from "react";
import useSWR from "swr";
import {
  Plus, RefreshCw, Trash2, MapPin, Camera, Edit2,
} from "lucide-react";
import { toast } from "sonner";

import { api, ApiError, swrFetcher } from "@/lib/api/client";
import { useAuthStore } from "@/lib/auth/store";
import { formatTanggalJam } from "@/lib/format/tanggal";
import FilterableSelect from "@/components/form/FilterableSelect";

type Photo = {
  id: string;
  observation: string;
  file: string;
  thumbnail: string | null;
  caption: string;
  taken_at: string | null;
};

type FieldObs = {
  id: string;
  contract: string;
  type: "MC-0" | "MC-INTERIM";
  type_display: string;
  location: string | null;
  location_code: string | null;
  observed_at: string;
  notes: string;
  document: string | null;
  photos: Photo[];
  photo_count: number;
};

type Paginated<T> = { count: number; results: T[] };

export default function MCListPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: contractId } = use(params);
  const { hasPerm } = useAuthStore();

  const { data, mutate } = useSWR<Paginated<FieldObs>>(
    `/field-observations/?contract=${contractId}&page_size=200`, swrFetcher,
  );

  const [showForm, setShowForm] = useState(false);
  const [editObs, setEditObs] = useState<FieldObs | null>(null);

  async function onDelete(obs: FieldObs) {
    if (!confirm(`Hapus ${obs.type} (${obs.location_code || "tanpa lokasi"})?`)) return;
    try {
      await api(`/field-observations/${obs.id}/`, { method: "DELETE" });
      toast.success("MC dihapus.");
      mutate();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <h2 className="text-lg font-semibold">Berita Acara MC (Field Observation)</h2>
          <p className="text-sm text-muted-fg">
            MC-0 (pengukuran awal, unik per kontrak) atau MC-Interim. Bukan dokumen legal,
            sumber justifikasi VO.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => mutate()} className="btn-ghost"><RefreshCw className="size-4" /></button>
          {hasPerm("mc.create") && (
            <button onClick={() => { setEditObs(null); setShowForm(true); }} className="btn-primary">
              <Plus className="size-4 mr-1" /> Buat MC
            </button>
          )}
        </div>
      </div>

      {data?.results?.length === 0 ? (
        <div className="card p-8 text-center text-muted-fg">Belum ada Berita Acara MC.</div>
      ) : (
        <div className="space-y-3">
          {data?.results?.map((obs) => (
            <MCCard
              key={obs.id}
              obs={obs}
              canEdit={hasPerm("mc.update")}
              canDelete={hasPerm("mc.delete")}
              onEdit={() => { setEditObs(obs); setShowForm(true); }}
              onDelete={() => onDelete(obs)}
              onPhotoUploaded={() => mutate()}
            />
          ))}
        </div>
      )}

      {showForm && (
        <MCFormModal
          contractId={contractId}
          editing={editObs}
          onClose={() => { setShowForm(false); setEditObs(null); }}
          onSaved={() => { setShowForm(false); setEditObs(null); mutate(); }}
        />
      )}
    </div>
  );
}

function MCCard({
  obs, canEdit, canDelete, onEdit, onDelete, onPhotoUploaded,
}: {
  obs: FieldObs; canEdit: boolean; canDelete: boolean;
  onEdit: () => void; onDelete: () => void; onPhotoUploaded: () => void;
}) {
  return (
    <div className="card overflow-hidden">
      <div className="p-4 flex items-start gap-3">
        <div className={`size-9 rounded-lg grid place-items-center text-xs font-bold shrink-0 ${
          obs.type === "MC-0" ? "bg-warning/10 text-warning" : "bg-primary/10 text-primary"
        }`}>
          {obs.type === "MC-0" ? "MC-0" : "MC"}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium">{obs.type_display}</span>
            {obs.location_code && (
              <span className="inline-flex items-center gap-1 text-xs bg-muted px-1.5 py-0.5 rounded">
                <MapPin className="size-3" /> {obs.location_code}
              </span>
            )}
            <span className="text-xs text-muted-fg ml-auto">
              {formatTanggalJam(obs.observed_at)}
            </span>
          </div>
          {obs.notes && (
            <p className="text-sm mt-1.5 whitespace-pre-wrap">{obs.notes}</p>
          )}
          <PhotoUploader
            obsId={obs.id}
            photos={obs.photos}
            canUpload={canEdit}
            onUploaded={onPhotoUploaded}
          />
        </div>
        <div className="flex gap-1 shrink-0">
          {canEdit && (
            <button onClick={onEdit} className="btn-ghost p-1.5"><Edit2 className="size-4" /></button>
          )}
          {canDelete && (
            <button onClick={onDelete} className="btn-ghost p-1.5 text-danger">
              <Trash2 className="size-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function PhotoUploader({
  obsId, photos, canUpload, onUploaded,
}: { obsId: string; photos: Photo[]; canUpload: boolean; onUploaded: () => void }) {
  const [uploading, setUploading] = useState(false);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const { useAuthStore } = await import("@/lib/auth/store");
      const access = useAuthStore.getState().access;
      const res = await fetch(`/api/v1/field-observations/${obsId}/photos/`, {
        method: "POST", body: fd,
        headers: access ? { Authorization: `Bearer ${access}` } : {},
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.error?.message || "Upload gagal.");
      }
      toast.success("Foto di-upload.");
      onUploaded();
      e.target.value = "";
    } catch (err: any) {
      toast.error(err.message || "Upload gagal.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="mt-3">
      {photos.length > 0 && (
        <div className="grid grid-cols-3 md:grid-cols-6 gap-1.5 mb-2">
          {photos.map((p) => (
            <a key={p.id} href={p.file} target="_blank" rel="noreferrer"
                className="aspect-square overflow-hidden rounded border bg-muted">
              <img src={p.thumbnail || p.file} alt={p.caption}
                    className="w-full h-full object-cover" />
            </a>
          ))}
        </div>
      )}
      {canUpload && (
        <label className="inline-flex items-center gap-1 text-xs text-primary hover:underline cursor-pointer">
          <Camera className="size-3" />
          {uploading ? "Mengunggah..." : `Tambah foto ${photos.length > 0 ? `(${photos.length})` : ""}`}
          <input type="file" accept="image/*" className="hidden"
                  onChange={onFile} disabled={uploading} />
        </label>
      )}
    </div>
  );
}

function MCFormModal({
  contractId, editing, onClose, onSaved,
}: {
  contractId: string; editing: FieldObs | null;
  onClose: () => void; onSaved: () => void;
}) {
  const [form, setForm] = useState({
    type: editing?.type ?? "MC-INTERIM",
    location: editing?.location ?? "",
    observed_at: editing?.observed_at?.slice(0, 16)
      ?? new Date().toISOString().slice(0, 16),
    notes: editing?.notes ?? "",
  });
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const body: any = {
        contract: contractId,
        type: form.type,
        location: form.location || null,
        observed_at: form.observed_at,
        notes: form.notes,
      };
      if (editing) {
        await api(`/field-observations/${editing.id}/`, { method: "PATCH", body });
      } else {
        await api(`/field-observations/`, { method: "POST", body });
      }
      toast.success("MC disimpan.");
      onSaved();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(err.message + (err.details ? "\n" + JSON.stringify(err.details) : ""));
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4">
      <form onSubmit={onSubmit} className="card p-6 w-full max-w-lg space-y-3">
        <h2 className="text-lg font-semibold">{editing ? "Edit" : "Buat"} Berita Acara MC</h2>

        <div>
          <label className="label">Tipe <span className="text-danger">*</span></label>
          <select className="input" value={form.type}
                  onChange={(e) => setForm({ ...form, type: e.target.value as any })}>
            <option value="MC-0">MC-0 (Pengukuran Awal, unik per kontrak)</option>
            <option value="MC-INTERIM">MC Interim</option>
          </select>
        </div>

        <div>
          <label className="label">Lokasi</label>
          <FilterableSelect
            value={form.location}
            onChange={(id) => setForm({ ...form, location: id || "" })}
            fetchUrl={`/locations/?contract=${contractId}&page_size=200`}
            getLabel={(l: any) => `${l.code} — ${l.name_kota || l.name_desa || ""}`}
            placeholder="Pilih lokasi (opsional)..."
          />
        </div>

        <div>
          <label className="label">Tanggal & Waktu Pengukuran <span className="text-danger">*</span></label>
          <input className="input" type="datetime-local" required value={form.observed_at}
                  onChange={(e) => setForm({ ...form, observed_at: e.target.value })} />
        </div>

        <div>
          <label className="label">Catatan</label>
          <textarea className="input" rows={4} value={form.notes}
                    onChange={(e) => setForm({ ...form, notes: e.target.value })}
                    placeholder="Kondisi lapangan, hasil pengukuran, dst." />
        </div>

        <p className="text-xs text-muted-fg pt-1">
          📷 Foto bukti dapat diunggah <strong>setelah</strong> MC ini disimpan —
          tombol "Tambah foto" akan tampil di kartu MC pada daftar di bawah.
        </p>

        <div className="flex gap-2 pt-2 border-t">
          <button type="button" onClick={onClose} className="btn-secondary flex-1" disabled={submitting}>Batal</button>
          <button type="submit" className="btn-primary flex-1" disabled={submitting}>
            {submitting ? "Menyimpan..." : "Simpan"}
          </button>
        </div>
      </form>
    </div>
  );
}
