import { formatCurrency } from "@/lib/format";
import type { PaymentPlan } from "@/types";

type ChartCardProps = {
  paymentPlan?: PaymentPlan | null;
};

const chartWidth = 720;
const chartHeight = 260;
const plot = {
  left: 58,
  right: 24,
  top: 24,
  bottom: 44,
};

export function ChartCard({ paymentPlan }: ChartCardProps) {
  const projection = buildProjection(paymentPlan);
  const paidCount = paymentPlan?.installments.filter((installment) => installment.status === "Ödendi").length || 0;
  const totalCount = paymentPlan?.installments.length || paymentPlan?.maturity_months || 36;
  const progressRatio = totalCount > 0 ? paidCount / totalCount : 0;
  const remainingPrincipal = paymentPlan?.remaining_principal ?? projection.currentRemaining;
  const paidAmount = Math.max(0, (paymentPlan?.approved_amount || projection.maxValue) - remainingPrincipal);
  const nextInstallment = paymentPlan?.installments.find((installment) => installment.status !== "Ödendi") || null;
  const headline = paymentPlan ? "Kalan borç projeksiyonu" : "Aylık ödeme eğilimi";

  return (
    <div className="rounded-xl border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.045),rgba(0,0,0,0.18))] p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.14em] text-primary">Ödeme Analitiği</p>
          <h3 className="mt-2 font-display text-2xl font-bold">{headline}</h3>
          <p className="mt-1 text-sm text-muted">
            {paymentPlan
              ? `${totalCount} aylık plan içinde ${paidCount} taksit tamamlandı.`
              : "Onay sonrası gerçek ödeme planı verisiyle güncellenir."}
          </p>
        </div>
        <div className="rounded-lg border border-white/10 bg-black/25 px-4 py-3 text-right">
          <span className="block text-xs uppercase tracking-[0.12em] text-muted">İlerleme</span>
          <strong className="mt-1 block text-xl text-secondary">%{Math.round(progressRatio * 100)}</strong>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <ChartMetric label="Ödenen ana para" value={formatCurrency(paidAmount)} tone="green" />
        <ChartMetric label="Kalan ana para" value={formatCurrency(remainingPrincipal)} tone="gold" />
        <ChartMetric label="Sıradaki taksit" value={nextInstallment ? formatCurrency(nextInstallment.amount) : "-"} tone="neutral" />
      </div>

      <div className="mt-5 overflow-hidden rounded-lg border border-white/10 bg-black/20 p-4">
        <svg className="h-72 w-full" viewBox={`0 0 ${chartWidth} ${chartHeight}`} role="img" aria-label="Kalan borç projeksiyon grafiği" preserveAspectRatio="none">
          <defs>
            <linearGradient id="principalFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#4edea3" stopOpacity=".28" />
              <stop offset="100%" stopColor="#4edea3" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="principalStroke" x1="0" x2="1" y1="0" y2="0">
              <stop offset="0%" stopColor="#f8bf00" />
              <stop offset="44%" stopColor="#4edea3" />
              <stop offset="100%" stopColor="#4edea3" />
            </linearGradient>
          </defs>

          {projection.gridLines.map((line) => (
            <g key={line.value}>
              <line x1={plot.left} x2={chartWidth - plot.right} y1={line.y} y2={line.y} stroke="rgba(255,255,255,.08)" strokeDasharray="4 8" />
              <text x={plot.left - 12} y={line.y + 4} textAnchor="end" className="fill-[#a9a39a] text-[11px]">
                {compactCurrency(line.value)}
              </text>
            </g>
          ))}

          {projection.monthTicks.map((tick) => (
            <g key={tick.label}>
              <line x1={tick.x} x2={tick.x} y1={plot.top} y2={chartHeight - plot.bottom} stroke="rgba(255,255,255,.045)" />
              <text x={tick.x} y={chartHeight - 16} textAnchor="middle" className="fill-[#a9a39a] text-[11px]">
                {tick.label}
              </text>
            </g>
          ))}

          <path d={projection.areaPath} fill="url(#principalFill)" />
          <path d={projection.linePath} fill="none" stroke="url(#principalStroke)" strokeLinecap="round" strokeWidth="4" />
          <path d={projection.paidPath} fill="none" stroke="#f8bf00" strokeLinecap="round" strokeWidth="4" />

          <circle cx={projection.currentPoint.x} cy={projection.currentPoint.y} r="6" fill="#f8bf00" stroke="#101113" strokeWidth="3" />
          <line
            x1={projection.currentPoint.x}
            x2={projection.currentPoint.x}
            y1={projection.currentPoint.y + 8}
            y2={chartHeight - plot.bottom}
            stroke="rgba(248,191,0,.45)"
            strokeDasharray="4 6"
          />
          <text x={projection.currentPoint.x + 12} y={Math.max(plot.top + 16, projection.currentPoint.y - 10)} className="fill-[#f8bf00] text-[12px] font-semibold">
            Bugün
          </text>
        </svg>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10">
        <div className="h-full rounded-full bg-secondary" style={{ width: `${Math.round(progressRatio * 100)}%` }} />
      </div>
      <div className="mt-2 flex items-center justify-between text-xs text-muted">
        <span>Başlangıç</span>
        <span>{paymentPlan ? `${paidCount}/${totalCount} taksit` : "Simülasyon"}</span>
        <span>Kapanış</span>
      </div>
    </div>
  );
}

function ChartMetric({ label, value, tone }: { label: string; value: string; tone: "gold" | "green" | "neutral" }) {
  const toneClass = tone === "green" ? "text-secondary" : tone === "gold" ? "text-primary" : "text-white";
  return (
    <div className="rounded-lg border border-white/10 bg-black/25 px-4 py-3">
      <span className="block text-xs uppercase tracking-[0.1em] text-muted">{label}</span>
      <strong className={`mt-1 block text-lg ${toneClass}`}>{value}</strong>
    </div>
  );
}

function buildProjection(paymentPlan?: PaymentPlan | null) {
  const termMonths = Math.max(1, paymentPlan?.maturity_months || 36);
  const maxValue = Math.max(1, paymentPlan?.approved_amount || 300000);
  const paidCount = paymentPlan?.installments.filter((installment) => installment.status === "Ödendi").length || 0;
  const currentRemaining = Math.max(0, paymentPlan?.remaining_principal ?? maxValue * 0.68);
  const pointCount = 13;
  const plotWidth = chartWidth - plot.left - plot.right;
  const plotHeight = chartHeight - plot.top - plot.bottom;

  const points = Array.from({ length: pointCount }, (_, index) => {
    const ratio = index / (pointCount - 1);
    const projectedRemaining = maxValue * (1 - ratio);
    const easedRemaining = Math.max(0, projectedRemaining - Math.sin(ratio * Math.PI) * maxValue * 0.06);
    return {
      month: Math.round(ratio * termMonths),
      x: plot.left + ratio * plotWidth,
      y: plot.top + (easedRemaining / maxValue) * plotHeight,
      value: easedRemaining,
    };
  });

  const paidRatio = paymentPlan ? Math.min(1, paidCount / Math.max(1, paymentPlan.installments.length || termMonths)) : 0.28;
  const currentPoint = {
    x: plot.left + paidRatio * plotWidth,
    y: plot.top + (currentRemaining / maxValue) * plotHeight,
  };
  const pathPoints = [
    ...points.filter((point) => point.x < currentPoint.x),
    currentPoint,
    ...points.filter((point) => point.x > currentPoint.x),
  ];
  const linePath = pathFromPoints(pathPoints);
  const paidPath = pathFromPoints(pathPoints.filter((point) => point.x <= currentPoint.x));
  const baselineY = chartHeight - plot.bottom;
  const areaPath = `${linePath} L ${chartWidth - plot.right} ${baselineY} L ${plot.left} ${baselineY} Z`;

  const gridValues = [maxValue, maxValue * 0.66, maxValue * 0.33, 0];
  const gridLines = gridValues.map((value) => ({
    value,
    y: plot.top + (1 - value / maxValue) * plotHeight,
  }));
  const monthTicks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => ({
    label: `${Math.round(ratio * termMonths)}. ay`,
    x: plot.left + ratio * plotWidth,
  }));

  return {
    areaPath,
    currentPoint,
    currentRemaining,
    gridLines,
    linePath,
    maxValue,
    monthTicks,
    paidPath,
  };
}

function pathFromPoints(points: Array<{ x: number; y: number }>) {
  if (!points.length) {
    return "";
  }
  return points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(" ");
}

function compactCurrency(value: number) {
  if (value >= 1_000_000) {
    return `₺${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `₺${Math.round(value / 1000)}B`;
  }
  return `₺${Math.round(value)}`;
}
