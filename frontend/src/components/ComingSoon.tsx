import { Construction } from "lucide-react";

export default function ComingSoon({
  title, module,
}: { title: string; module: string }) {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{title}</h1>
      <div className="card p-8 text-center">
        <div className="size-12 mx-auto rounded-full bg-warning/10 text-warning grid place-items-center mb-4">
          <Construction className="size-6" />
        </div>
        <h2 className="font-semibold mb-1">Belum Tersedia</h2>
        <p className="text-sm text-muted-fg">
          Halaman ini akan diaktifkan saat <strong>{module}</strong> selesai diimplementasikan.
        </p>
      </div>
    </div>
  );
}
