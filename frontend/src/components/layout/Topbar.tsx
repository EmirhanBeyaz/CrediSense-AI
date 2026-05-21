type TopbarProps = {
  title: string;
  subtitle: string;
};

export function Topbar({ title, subtitle }: TopbarProps) {
  return (
    <header className="mb-7 flex items-start justify-between gap-4">
      <div>
        <p className="mb-2 font-mono text-xs font-semibold uppercase tracking-[0.16em] text-primary">CrediSense AI</p>
        <h1 className="font-display text-3xl font-bold md:text-4xl">{title}</h1>
        {subtitle ? <p className="mt-2 max-w-3xl text-sm text-muted">{subtitle}</p> : null}
      </div>
      <button className="grid h-12 w-12 place-items-center rounded-xl border border-white/10 bg-white/[0.04] text-primary" type="button">
        <span className="material-symbols-outlined">notifications</span>
      </button>
    </header>
  );
}
