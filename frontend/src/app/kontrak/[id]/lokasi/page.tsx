"use client";

import { use, useState } from "react";
import useSWR from "swr";
import { Plus, Edit2, Trash2, MapPin, Building, ChevronDown, ChevronRight, X } from "lucide-react";
import { toast } from "sonner";

import { api, ApiError, swrFetcher } from "@/lib/api/client";
import { useAuthStore } from "@/lib/auth/store";
import FilterableSelect from "@/components/form/FilterableSelect";

type Facility = {
  id: string;
  code: string;
  name: string;
  master_facility: string;
  master_facility_name: string;
  display_order: number;
};

type Location = {
  id: string;
  contract: string;
  code: string;
  name_desa: string;
  name_kecamatan: string;
  name_kota: string;
  name_provinsi: string;
  full_address: string;
  latitude: string | null;
  longitude: string | null;
  has_coordinates: boolean;
  konsultan: string | null;
  konsultan_name: string | null;
  notes: string;
  facilities: Facility[];
};

type Paginated<T> = { count: number; results: T[] };

export default function LokasiPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: contractId } = use(params);
  const { hasPerm } = useAuthStore();
  const { data, mutate } = useSWR<Paginated<Location>>(
    `/locations/?contract=${contractId}&page_size=200`, swrFetcher,
  );
  const [showLocForm, setShowLocForm] = useState(false);
  const [editLoc, setEditLoc] = useState<Location | null>(null);

  // facility modal state
  const [facLocation, setFacLocation] = useState<Location | null>(null);
  const [editFac, setEditFac] = useState<Facility | null>(null);
  const [showFacForm, setShowFacForm] = useState(false);

  async function deleteLocation(loc: Location) {
    if (!confirm(`Hapus lokasi "${loc.code}" beserta seluruh fasilitasnya tidak akan dilakukan; lokasi akan dihapus, fasilitas perlu dihapus terpisah.\n\nLanjutkan?`)) return;
    try {
      await api(`/locations/${loc.id}/`, { method: "DELETE" });
      toast.success("Lokasi dihapus.");
      mutate();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    }
  }

  async function deleteFacility(fac: Facility) {
    if (!confirm(`Hapus fasilitas "${fac.code} - ${fac.name}"?`)) return;
    try {
      await api(`/facilities/${fac.id}/`, { method: "DELETE" });
      toast.success("Fasilitas dihapus.");
      mutate();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <h2 className="text-lg font-semibold">Lokasi & Fasilitas</h2>
          <p className="text-sm text-muted-fg">
            Setiap lokasi wajib punya koordinat dan minimal 1 fasilitas (gate aktivasi).
          </p>
        </div>
        {hasPerm("location.create") && (
          <button onClick={() => { setEditLoc(null); setShowLocForm(true); }} className="btn-primary">
            <Plus className="size-4 mr-1" /> Tambah Lokasi
          </button>
        )}
      </div>

      {data?.results?.length === 0 && (
        <div className="card p-8 text-center">
          <MapPin className="size-8 mx-auto text-muted-fg mb-2" />
          <p className="text-sm text-muted-fg">Belum ada lokasi.</p>
        </div>
      )}

      <div className="space-y-3">
        {data?.results?.map((loc) => (
          <LocationCard
            key={loc.id}
            location={loc}
            canEdit={hasPerm("location.update")}
            canDelete={hasPerm("location.delete")}
            canCreateFacility={hasPerm("facility.create")}
            canEditFacility={hasPerm("facility.update")}
            canDeleteFacility={hasPerm("facility.delete")}
            onEdit={() => { setEditLoc(loc); setShowLocForm(true); }}
            onDelete={() => deleteLocation(loc)}
            onAddFacility={() => { setFacLocation(loc); setEditFac(null); setShowFacForm(true); }}
            onEditFacility={(fac) => { setFacLocation(loc); setEditFac(fac); setShowFacForm(true); }}
            onDeleteFacility={deleteFacility}
          />
        ))}
      </div>

      {showLocForm && (
        <LocationFormModal
          contractId={contractId}
          editing={editLoc}
          onClose={() => { setShowLocForm(false); setEditLoc(null); }}
          onSaved={() => { setShowLocForm(false); setEditLoc(null); mutate(); }}
        />
      )}
      {showFacForm && facLocation && (
        <FacilityFormModal
          location={facLocation}
          editing={editFac}
          onClose={() => { setShowFacForm(false); setEditFac(null); setFacLocation(null); }}
          onSaved={() => { setShowFacForm(false); setEditFac(null); setFacLocation(null); mutate(); }}
        />
      )}
    </div>
  );
}

type LocationCardProps = {
  location: Location;
  canEdit: boolean;
  canDelete: boolean;
  canCreateFacility: boolean;
  canEditFacility: boolean;
  canDeleteFacility: boolean;
  onEdit: () => void;
  onDelete: () => void;
  onAddFacility: () => void;
  onEditFacility: (fac: Facility) => void;
  onDeleteFacility: (fac: Facility) => void;
};

function LocationCard({
  location, canEdit, canDelete, canCreateFacility,
  canEditFacility, canDeleteFacility,
  onEdit, onDelete, onAddFacility, onEditFacility, onDeleteFacility,
}: LocationCardProps) {
  const [open, setOpen] = useState(true);
  const loc: Location = location;

  return (
    <div className="card">
      <div className="p-4 flex items-start gap-3">
        <button onClick={() => setOpen(!open)} className="btn-ghost p-1 mt-0.5">
          {open ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">{loc.code}</span>
            <h3 className="font-medium truncate">
              {[loc.name_desa, loc.name_kecamatan, loc.name_kota, loc.name_provinsi]
                .filter(Boolean).join(", ") || "(tanpa alamat)"}
            </h3>
          </div>
          <div className="mt-1 flex items-center gap-3 text-xs text-muted-fg">
            {loc.has_coordinates ? (
              <span className="flex items-center gap-1 text-success">
                <MapPin className="size-3" /> {loc.latitude}, {loc.longitude}
              </span>
            ) : (
              <span className="flex items-center gap-1 text-warning">
                <MapPin className="size-3" /> Koordinat belum diisi
              </span>
            )}
            {loc.konsultan_name && (
              <span>Konsultan: {loc.konsultan_name}</span>
            )}
            <span>{loc.facilities.length} fasilitas</span>
          </div>
        </div>
        <div className="flex gap-1 shrink-0">
          {canEdit && (
            <button onClick={onEdit} className="btn-ghost p-1.5" title="Edit lokasi">
              <Edit2 className="size-4" />
            </button>
          )}
          {canDelete && (
            <button onClick={onDelete} className="btn-ghost p-1.5 text-danger" title="Hapus lokasi">
              <Trash2 className="size-4" />
            </button>
          )}
        </div>
      </div>

      {open && (
        <div className="border-t bg-muted/20 p-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium">Fasilitas</h4>
            {canCreateFacility && (
              <button onClick={onAddFacility} className="text-primary text-xs hover:underline inline-flex items-center gap-1">
                <Plus className="size-3" /> Tambah Fasilitas
              </button>
            )}
          </div>
          {loc.facilities.length === 0 ? (
            <div className="text-xs text-muted-fg italic">Belum ada fasilitas.</div>
          ) : (
            <ul className="space-y-1.5">
              {loc.facilities.map((f) => (
                <li key={f.id} className="flex items-center gap-2 text-sm bg-card border rounded-lg px-3 py-2">
                  <Building className="size-3.5 text-muted-fg shrink-0" />
                  <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">{f.code}</span>
                  <span className="font-medium truncate flex-1">{f.name}</span>
                  <span className="text-xs text-muted-fg hidden md:inline">{f.master_facility_name}</span>
                  <div className="flex gap-1">
                    {canEditFacility && (
                      <button onClick={() => onEditFacility(f)} className="btn-ghost p-1" title="Edit">
                        <Edit2 className="size-3" />
                      </button>
                    )}
                    {canDeleteFacility && (
                      <button onClick={() => onDeleteFacility(f)} className="btn-ghost p-1 text-danger" title="Hapus">
                        <Trash2 className="size-3" />
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function LocationFormModal({
  contractId, editing, onClose, onSaved,
}: {
  contractId: string;
  editing: Location | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({
    code: editing?.code ?? "",
    name_desa: editing?.name_desa ?? "",
    name_kecamatan: editing?.name_kecamatan ?? "",
    name_kota: editing?.name_kota ?? "",
    name_provinsi: editing?.name_provinsi ?? "",
    full_address: editing?.full_address ?? "",
    latitude: editing?.latitude ?? "",
    longitude: editing?.longitude ?? "",
    konsultan: editing?.konsultan ?? "",
    notes: editing?.notes ?? "",
  });
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const body: any = {
        ...form,
        contract: contractId,
        latitude: form.latitude || null,
        longitude: form.longitude || null,
        konsultan: form.konsultan || null,
      };
      if (editing) {
        await api(`/locations/${editing.id}/`, { method: "PATCH", body });
        toast.success("Lokasi diperbarui.");
      } else {
        await api(`/locations/`, { method: "POST", body });
        toast.success("Lokasi dibuat.");
      }
      onSaved();
    } catch (err) {
      if (err instanceof ApiError) {
        const detail = err.details ? "\n" + JSON.stringify(err.details) : "";
        toast.error(`${err.message}${detail}`);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4">
      <form onSubmit={onSubmit} className="card p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">{editing ? "Edit Lokasi" : "Tambah Lokasi"}</h2>
          <button type="button" onClick={onClose} className="btn-ghost p-1.5"><X className="size-4" /></button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Kode <span className="text-danger">*</span></label>
            <input className="input" required value={form.code}
                    onChange={(e) => setForm({ ...form, code: e.target.value })}
                    placeholder="L1, L2, dst." />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Desa</label>
            <input className="input" value={form.name_desa}
                    onChange={(e) => setForm({ ...form, name_desa: e.target.value })} />
          </div>
          <div>
            <label className="label">Kecamatan</label>
            <input className="input" value={form.name_kecamatan}
                    onChange={(e) => setForm({ ...form, name_kecamatan: e.target.value })} />
          </div>
          <div>
            <label className="label">Kota / Kabupaten</label>
            <input className="input" value={form.name_kota}
                    onChange={(e) => setForm({ ...form, name_kota: e.target.value })} />
          </div>
          <div>
            <label className="label">Provinsi</label>
            <input className="input" value={form.name_provinsi}
                    onChange={(e) => setForm({ ...form, name_provinsi: e.target.value })} />
          </div>
        </div>
        <div>
          <label className="label">Alamat Lengkap (untuk surat)</label>
          <textarea className="input" rows={2} value={form.full_address}
                    onChange={(e) => setForm({ ...form, full_address: e.target.value })} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Latitude <span className="text-danger">*</span></label>
            <input className="input font-mono" type="number" step="0.0000001"
                    min="-90" max="90"
                    value={form.latitude}
                    onChange={(e) => setForm({ ...form, latitude: e.target.value })}
                    placeholder="-6.2000000" />
          </div>
          <div>
            <label className="label">Longitude <span className="text-danger">*</span></label>
            <input className="input font-mono" type="number" step="0.0000001"
                    min="-180" max="180"
                    value={form.longitude}
                    onChange={(e) => setForm({ ...form, longitude: e.target.value })}
                    placeholder="106.8000000" />
          </div>
        </div>
        <p className="text-xs text-muted-fg">
          Koordinat wajib utk muncul di peta dashboard. Bisa diambil dari Google Maps:
          klik kanan pada titik → koordinat akan tampil di pojok atas.
        </p>
        <div>
          <label className="label">Konsultan MK Pengawas</label>
          <FilterableSelect
            value={form.konsultan}
            onChange={(id) => setForm({ ...form, konsultan: id || "" })}
            fetchUrl="/companies/lookup/?type=KONSULTAN"
            getLabel={(c: any) => `${c.code} - ${c.name}`}
            placeholder="Pilih konsultan..."
            initialItem={editing && form.konsultan ? { id: form.konsultan, code: "", name: editing.konsultan_name || "" } as any : null}
          />
          <p className="text-xs text-muted-fg mt-1">
            Konsultan dipilih per lokasi (bukan per kontrak). Hanya konsultan ini yang
            dapat input laporan untuk lokasi ini.
          </p>
        </div>
        <div>
          <label className="label">Catatan</label>
          <textarea className="input" rows={2} value={form.notes}
                    onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        </div>
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

function FacilityFormModal({
  location, editing, onClose, onSaved,
}: {
  location: Location;
  editing: Facility | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({
    code: editing?.code ?? "",
    name: editing?.name ?? "",
    master_facility: editing?.master_facility ?? "",
    display_order: editing?.display_order ?? 0,
  });
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const body: any = { ...form, location: location.id };
      if (editing) {
        await api(`/facilities/${editing.id}/`, { method: "PATCH", body });
        toast.success("Fasilitas diperbarui.");
      } else {
        await api(`/facilities/`, { method: "POST", body });
        toast.success("Fasilitas dibuat.");
      }
      onSaved();
    } catch (err) {
      if (err instanceof ApiError) {
        const detail = err.details ? "\n" + JSON.stringify(err.details) : "";
        toast.error(`${err.message}${detail}`);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4">
      <form onSubmit={onSubmit} className="card p-6 w-full max-w-md space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">
            {editing ? "Edit Fasilitas" : "Tambah Fasilitas"}
          </h2>
          <button type="button" onClick={onClose} className="btn-ghost p-1.5"><X className="size-4" /></button>
        </div>
        <p className="text-xs text-muted-fg">Lokasi: <strong>{location.code}</strong></p>
        <div>
          <label className="label">Kode <span className="text-danger">*</span></label>
          <input className="input" required value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value })}
                  placeholder="F1, F2, dst." />
        </div>
        <div>
          <label className="label">Tipe Fasilitas <span className="text-danger">*</span></label>
          <FilterableSelect
            value={form.master_facility}
            onChange={(id) => setForm({ ...form, master_facility: id || "" })}
            fetchUrl="/master-facilities/lookup/"
            getLabel={(m: any) => `${m.code} - ${m.name}`}
            placeholder="Pilih tipe..."
            required
            initialItem={editing && form.master_facility
              ? { id: form.master_facility, code: "", name: editing.master_facility_name } as any
              : null}
          />
        </div>
        <div>
          <label className="label">Nama Fasilitas <span className="text-danger">*</span></label>
          <input className="input" required value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Gudang Beku 1" />
        </div>
        <div>
          <label className="label">Urutan Tampil</label>
          <input className="input" type="number" min="0" value={form.display_order}
                  onChange={(e) => setForm({ ...form, display_order: parseInt(e.target.value || "0") })} />
        </div>
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
