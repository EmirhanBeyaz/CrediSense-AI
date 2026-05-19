type MetricCardProps = {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "gold" | "green" | "red" | "neutral";
};

const toneClass = {
  gold: "text-primary",
  green: "text-secondary",
  red: "text-danger",
  neutral: "text-white",
};

export function MetricCard({ label, value, hint, tone = "gold" }: MetricCardProps) {
  return (
    <div className="rounded-lg border border-white/10 bg-black/25 p-4">
      <span className="text-sm text-muted">{label}</span>
      <strong className={`mt-2 block font-display text-2xl ${toneClass[tone]}`}>{value}</strong>
      {hint ? <small className="mt-2 block text-xs text-muted">{hint}</small> : null}
    </div>
  );
}
