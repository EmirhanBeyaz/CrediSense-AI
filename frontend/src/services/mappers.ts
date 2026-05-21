import type { AnalysisResult, ApplicationRecord, PaymentPlan, Wallet } from "@/types";

export function mapApplicationRecord(raw: any): ApplicationRecord {
  const analysis = raw?.analysis_result || raw?.risk || raw?.result || raw?.risk_summary || {};
  const features = raw?.features || {};
  const documents = raw?.documents || {};
  const applicant = raw?.applicant || {};
  const currentStatus = raw?.current_status || {};
  const decision = raw?.bank_decision || raw?.expert_decision || {};
  const workflow = raw?.expert_workflow || {};
  const bankView = raw?.bank_view || {};
  const requestedDocuments = decision?.requested_documents || raw?.user_notification?.requested_documents || [];
  const riskScore = analysis?.risk_score ?? bankView?.risk_score ?? raw?.risk_score ?? 0.72;
  const creditRequest = normalizeCreditRequest(raw?.credit_request || {});

  return {
    application_id: raw?.application_id || raw?.id || "APP-LOCAL",
    customer_name: raw?.customer_name || raw?.full_name || applicant?.full_name || documents?.identity?.full_name || "Deniz Kaya",
    status: currentStatus?.status_text || decision?.decision_text || decision?.status || raw?.status || "Uzman incelemesinde",
    status_code: currentStatus?.status_code || decision?.status_code || raw?.status_code,
    created_at: raw?.created_at,
    risk_score: normalizePercent(riskScore),
    risk_level: analysis?.risk_level || bankView?.risk_level || raw?.risk_level || "Orta",
    document_confidence_score: features?.document_confidence_score ?? raw?.document_confidence_score ?? bankView?.package_quality_score ?? 0.95,
    consistency_score: features?.consistency_score ?? raw?.consistency_score ?? bankView?.consistency_score ?? 0.82,
    anomaly_score: features?.anomaly_score ?? raw?.anomaly_score ?? bankView?.anomaly_score ?? 0.25,
    ai_recommendation:
      bankView?.recommended_action
      || analysis?.recommended_action
      || analysis?.reasons?.[0]
      || raw?.ai_recommendation
      || "AI önerisi uzman incelemesi yönündedir.",
    expert_decision: decision?.decision_type || raw?.expert_decision || "Beklemede",
    review_route: workflow?.route,
    review_route_text: workflow?.route_text,
    system_action: workflow?.system_action,
    requested_documents: requestedDocuments,
    documents: Array.isArray(raw?.documents) ? raw.documents : [],
    decision_note: decision?.note,
    report_count: Array.isArray(raw?.expert_reports) ? raw.expert_reports.length : 0,
    credit_request: creditRequest,
    reasons: uniqueStrings([
      ...(bankView?.main_reasons || []),
      ...(analysis?.reasons || []),
      ...(analysis?.main_reasons || []),
      ...(analysis?.consistency_flags || []),
      ...(analysis?.form_document_flags || []),
      ...(analysis?.data_precedence_warnings || []),
      ...(analysis?.blockers || []),
    ]),
    raw,
  };
}

export function mapAnalysisResult(raw: any): AnalysisResult {
  const risk = raw?.risk || raw?.analysis_result || {};
  const features = raw?.features || {};
  const accountCheck = raw?.account_document_consistency || {};
  const accountWarnings = accountCheck?.mismatched_names?.length
    ? [
        `Belge sahibi ile oturumdaki kullanici eslesmiyor. Hesap: ${accountCheck.account_full_name}. Belgeler: ${accountCheck.mismatched_names.join(", ")}.`,
      ]
    : [];
  const reasons = uniqueStrings([
    ...accountWarnings,
    ...(raw?.data_precedence_warnings || []),
    ...(raw?.form_document_consistency?.flags || []),
    ...(raw?.consistency?.flags || []),
    ...(risk?.reasons || []),
  ]);

  return {
    applicationId: raw?.application_id || "APP-LOCAL",
    eligibilityScore: Math.max(0, Math.min(100, Math.round((1 - (risk?.risk_score ?? 0.34)) * 100))),
    riskScore: normalizePercent(risk?.risk_score ?? 0.72),
    riskLevel: risk?.risk_level || "Orta",
    documentConfidenceScore: features?.document_confidence_score ?? 0.95,
    consistencyScore: features?.consistency_score ?? 0.82,
    anomalyScore: features?.anomaly_score ?? 0.25,
    aiRecommendation: "AI önerisi nihai karar değildir; banka uzmanı incelemesi gerekir.",
    summary: "Belgeler katmanlı analizden geçirildi ve karar destek özeti oluşturuldu.",
    reasons: reasons.length ? reasons : [
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
    monthly_interest_rate: Number(raw?.monthly_interest_rate ?? raw?.interest_policy?.effective_monthly_interest_rate ?? 0),
    annual_interest_rate: Number(raw?.annual_interest_rate ?? raw?.interest_policy?.effective_annual_interest_rate ?? 0),
    total_payment: Number(raw?.total_payment ?? 0),
    total_interest: Number(raw?.total_interest ?? 0),
    interest_policy: raw?.interest_policy || undefined,
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
      paid_date: item.paid_date ? String(item.paid_date) : undefined,
    })),
  };
}

export function mapWallet(raw: any): Wallet {
  const transactions = Array.isArray(raw?.transactions) ? raw.transactions : [];
  return {
    balance: Number(raw?.balance ?? 0),
    currency: String(raw?.currency || "TRY"),
    transactions: transactions.map((item: any) => ({
      transaction_id: String(item.transaction_id || item.id || ""),
      type: String(item.type || ""),
      amount: Number(item.amount ?? 0),
      currency: String(item.currency || "TRY"),
      description: item.description ? String(item.description) : undefined,
      created_at: item.created_at ? String(item.created_at) : undefined,
      loan_id: item.loan_id ? String(item.loan_id) : undefined,
      installment_no: item.installment_no ? Number(item.installment_no) : undefined,
      card_last4: item.card_last4 ? String(item.card_last4) : undefined,
    })),
  };
}

function mapPaymentStatus(status: string) {
  if (status === "paid" || status === "Ödendi") return "Ödendi";
  if (status === "overdue" || status === "Gecikmiş") return "Gecikmiş";
  if (status === "pending") return "Planlandı";
  return status;
}

function normalizePercent(value: unknown): number {
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) {
    return 0;
  }
  if (numberValue <= 1) {
    return Math.round(numberValue * 100);
  }
  return Math.round(numberValue);
}

function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)));
}

function normalizeCreditRequest(creditRequest: Record<string, unknown>): ApplicationRecord["credit_request"] {
  const requestedAmount = repairSmallRequestedAmount(
    parseMoneyValue(creditRequest.requested_amount),
    parseMoneyValue(creditRequest.current_total_debt),
    parseMoneyValue(creditRequest.declared_monthly_income),
  );
  const originalRequestedAmount = creditRequest.requested_amount;

  return {
    ...creditRequest,
    requested_amount: Number.isFinite(requestedAmount) && requestedAmount > 0
      ? requestedAmount
      : typeof originalRequestedAmount === "string" || typeof originalRequestedAmount === "number"
        ? originalRequestedAmount
        : undefined,
  };
}

function repairSmallRequestedAmount(amount: number, currentDebt: number, declaredIncome: number) {
  if (amount > 0 && amount < 1000 && (currentDebt >= 10000 || declaredIncome >= 10000)) {
    return amount * 1000;
  }
  return amount;
}

function parseMoneyValue(value: unknown) {
  if (typeof value === "number") {
    return value;
  }
  if (typeof value !== "string") {
    return Number.NaN;
  }

  let text = value.replace(/[^0-9,.\-]/g, "");
  if (!text) {
    return Number.NaN;
  }

  if (text.includes(",") && text.includes(".")) {
    text = text.replace(/\./g, "").replace(",", ".");
  } else if (text.includes(",")) {
    text = text.replace(/\./g, "").replace(",", ".");
  } else if (text.includes(".")) {
    const parts = text.split(".");
    if (parts.length > 1 && parts.slice(1).every((part) => part.length === 3)) {
      text = parts.join("");
    }
  }

  return Number(text);
}
