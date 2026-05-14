import type { AnalysisResult, ApplicationRecord, PaymentPlan } from "@/types";

export function mapApplicationRecord(raw: any): ApplicationRecord {
  const analysis = raw?.analysis_result || raw?.risk || raw?.result || {};
  const features = raw?.features || {};
  const documents = raw?.documents || {};
  const decision = raw?.bank_decision || raw?.expert_decision || {};

  return {
    application_id: raw?.application_id || raw?.id || "APP-LOCAL",
    customer_name: raw?.customer_name || raw?.full_name || documents?.identity?.full_name || "Deniz Kaya",
    status: decision?.status || raw?.status || "Uzman incelemesinde",
    created_at: raw?.created_at,
    risk_score: Math.round((analysis?.risk_score ?? raw?.risk_score ?? 0.72) * 100),
    risk_level: analysis?.risk_level || raw?.risk_level || "Orta",
    document_confidence_score: features?.document_confidence_score ?? raw?.document_confidence_score ?? 0.95,
    consistency_score: features?.consistency_score ?? raw?.consistency_score ?? 0.82,
    anomaly_score: features?.anomaly_score ?? raw?.anomaly_score ?? 0.25,
    ai_recommendation: analysis?.reasons?.[0] || raw?.ai_recommendation || "AI önerisi uzman incelemesi yönündedir.",
    expert_decision: decision?.decision_type || raw?.expert_decision || "Beklemede",
    raw,
  };
}

export function mapAnalysisResult(raw: any): AnalysisResult {
  const risk = raw?.risk || raw?.analysis_result || {};
  const features = raw?.features || {};

  return {
    applicationId: raw?.application_id || "APP-LOCAL",
    eligibilityScore: Math.max(0, Math.min(100, Math.round((1 - (risk?.risk_score ?? 0.34)) * 100))),
    riskScore: Math.round((risk?.risk_score ?? 0.72) * 100),
    riskLevel: risk?.risk_level || "Orta",
    documentConfidenceScore: features?.document_confidence_score ?? 0.95,
    consistencyScore: features?.consistency_score ?? 0.82,
    anomalyScore: features?.anomaly_score ?? 0.25,
    aiRecommendation: "AI önerisi nihai karar değildir; banka uzmanı incelemesi gerekir.",
    summary: "Belgeler katmanlı analizden geçirildi ve karar destek özeti oluşturuldu.",
    reasons: risk?.reasons || [
      "Belgeler okunabilir durumda.",
      "Gelir ve banka hareketleri karşılaştırıldı.",
      "Nihai karar banka uzmanı tarafından verilmelidir.",
    ],
    raw,
  };
}

export function mapPaymentPlan(raw: any): PaymentPlan {
  const schedule = raw?.schedule || raw?.installments || [];

  return {
    loan_id: raw?.loan_id || "LOAN-LOCAL",
    approved_amount: Number(raw?.principal ?? raw?.approved_amount ?? 0),
    monthly_payment: Number(raw?.monthly_payment ?? 0),
    maturity_months: Number(raw?.term_months ?? raw?.maturity_months ?? 0),
    remaining_principal: Number(
      raw?.current_debt
      ?? raw?.payment_summary?.remaining_principal_after_last_payment
      ?? raw?.remaining_principal
      ?? 0,
    ),
    installments: schedule.map((item: any) => ({
      installment_no: Number(item.installment_no ?? item.no ?? 0),
      due_date: String(item.due_date ?? ""),
      amount: Number(item.payment_amount ?? item.amount ?? 0),
      status: mapPaymentStatus(String(item.status ?? "pending")),
    })),
  };
}

function mapPaymentStatus(status: string) {
  if (status === "paid" || status === "Ödendi") return "Ödendi";
  if (status === "overdue" || status === "Gecikmiş") return "Gecikmiş";
  if (status === "pending") return "Planlandı";
  return status;
}
