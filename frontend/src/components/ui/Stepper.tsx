import type { AnalysisStage } from "@/types";

type StepperProps = {
  stages: AnalysisStage[];
};

export function Stepper({ stages }: StepperProps) {
  return (
    <div className="grid gap-3 md:grid-cols-5">
      {stages.map((stage, index) => (
        <article
          className={`rounded-lg border p-4 transition ${
            stage.status === "calisiyor"
              ? "border-primary/60 bg-primary/10 shadow-glow"
              : stage.status === "tamamlandi"
                ? "border-secondary/40 bg-secondary/10"
                : stage.status === "hata"
                  ? "border-danger/50 bg-danger/10"
                  : "border-white/10 bg-black/20"
          }`}
          key={stage.id}
        >
          <span className="gold-gradient mb-4 grid h-9 w-9 place-items-center rounded-lg text-sm font-bold text-black">
            {String(index + 1).padStart(2, "0")}
          </span>
          <strong className="block leading-tight">{stage.title}</strong>
          <small className="mt-2 block text-xs text-muted">{stage.description}</small>
          <em className="mt-3 block text-xs not-italic text-secondary">{statusLabel(stage.status)}</em>
          {stage.status === "hata" && stage.errorMessage ? (
            <p className="mt-3 rounded-lg border border-danger/40 bg-danger/10 p-2 text-xs leading-relaxed text-red-100">
              {stage.errorMessage}
            </p>
          ) : null}
        </article>
      ))}
    </div>
  );
}

function statusLabel(status: AnalysisStage["status"]) {
  if (status === "calisiyor") return "İşleniyor";
  if (status === "tamamlandi") return "Tamamlandı";
  if (status === "hata") return "Hata";
  return "Bekliyor";
}
