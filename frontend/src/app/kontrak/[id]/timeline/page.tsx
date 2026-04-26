"use client";

import { use } from "react";
import useSWR from "swr";
import { Calendar } from "lucide-react";

import { swrFetcher } from "@/lib/api/client";
import { formatTanggalJam } from "@/lib/format/tanggal";

type Event = { kind: string; label: string; date: string; detail: string };

export default function TimelinePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data } = useSWR<{ events: Event[] }>(`/contracts/${id}/timeline/`, swrFetcher);

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">Timeline Kontrak</h2>
      <div className="card p-4">
        {data?.events?.length === 0 && (
          <p className="text-sm text-muted-fg">Belum ada event.</p>
        )}
        <ol className="relative border-l-2 border-border pl-6 space-y-4">
          {data?.events?.map((e, i) => (
            <li key={i} className="relative">
              <span className="absolute -left-[31px] size-4 rounded-full bg-primary border-2 border-background" />
              <div className="flex items-center gap-2 text-xs text-muted-fg mb-0.5">
                <Calendar className="size-3" /> {formatTanggalJam(e.date)}
              </div>
              <div className="font-medium">{e.label}</div>
              {e.detail && <div className="text-sm text-muted-fg">{e.detail}</div>}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
