type EmptyStateProps = {
  title: string;
  description: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="rounded-xl border border-dashed border-white/15 bg-white/[0.03] p-8 text-center">
      <span className="material-symbols-outlined mx-auto mb-3 grid h-12 w-12 place-items-center rounded-lg bg-white/5 text-primary">
        inbox
      </span>
      <strong className="block">{title}</strong>
      <p className="mx-auto mt-2 max-w-xl text-sm text-muted">{description}</p>
    </div>
  );
}
