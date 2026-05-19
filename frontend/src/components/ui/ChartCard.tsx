export function ChartCard() {
  return (
    <div className="rounded-xl border border-white/10 bg-black/25 p-4">
      <div className="mb-4 flex items-center justify-between">
        <strong>Aylık ödeme eğilimi</strong>
        <span className="text-xs text-muted">Simülasyon</span>
      </div>
      <svg className="h-56 w-full" viewBox="0 0 640 220" role="img" aria-label="Ödeme grafiği">
        <defs>
          <linearGradient id="chartFillReact" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#4edea3" stopOpacity=".32" />
            <stop offset="100%" stopColor="#4edea3" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path
          d="M20 180 C120 160 140 142 230 132 C320 120 340 86 430 78 C520 68 540 36 620 28 L620 210 L20 210 Z"
          fill="url(#chartFillReact)"
        />
        <path
          d="M20 180 C120 160 140 142 230 132 C320 120 340 86 430 78 C520 68 540 36 620 28"
          fill="none"
          stroke="#4edea3"
          strokeLinecap="round"
          strokeWidth="4"
        />
      </svg>
    </div>
  );
}
