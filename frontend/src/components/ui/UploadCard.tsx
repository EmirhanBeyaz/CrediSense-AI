import type { UploadedDocument } from "@/types";
import { StatusBadge } from "./StatusBadge";

type UploadCardProps = {
  document: UploadedDocument;
  onUpload: (documentId: string, file: File) => void;
};

export function UploadCard({ document, onUpload }: UploadCardProps) {
  const tone = document.status === "yuklendi" || document.status === "onaylandi" ? "green" : document.status === "eksik" ? "red" : "neutral";

  return (
    <label className="group block rounded-xl border border-white/10 bg-black/25 p-4 transition hover:-translate-y-1 hover:border-primary/40 hover:shadow-glow">
      <input
        className="hidden"
        type="file"
        accept="application/pdf,.pdf"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onUpload(document.id, file);
        }}
      />
      <div className="flex items-center gap-4">
        <span className="material-symbols-outlined grid h-11 w-11 place-items-center rounded-lg bg-primary/15 text-primary">
          upload_file
        </span>
        <div className="min-w-0 flex-1">
          <strong className="block truncate">{document.name}</strong>
          <small className="block truncate text-sm text-muted">{document.file?.name || document.type}</small>
        </div>
        <StatusBadge tone={tone}>{document.status === "yuklendi" ? "Yüklendi" : document.status === "bekliyor" ? "Bekliyor" : document.status}</StatusBadge>
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10">
        <i className="block h-full rounded-full bg-secondary transition-all" style={{ width: `${document.progress}%` }} />
      </div>
    </label>
  );
}
