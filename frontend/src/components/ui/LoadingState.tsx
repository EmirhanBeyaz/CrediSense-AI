export function LoadingState({ label = "Yükleniyor" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-black/20 p-4 text-muted">
      <span className="material-symbols-outlined animate-spin text-primary">progress_activity</span>
      <span>{label}</span>
    </div>
  );
}
