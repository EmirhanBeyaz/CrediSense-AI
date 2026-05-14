type StatusBadgeProps = {
  children: string;
  tone?: "gold" | "green" | "red" | "neutral";
};

const toneClass = {
  gold: "border-primary/30 bg-primary/10 text-primary",
  green: "border-secondary/30 bg-secondary/10 text-secondary",
  red: "border-danger/30 bg-danger/10 text-danger",
  neutral: "border-white/10 bg-white/5 text-muted",
};

export function StatusBadge({ children, tone = "neutral" }: StatusBadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${toneClass[tone]}`}>
      {children}
    </span>
  );
}
