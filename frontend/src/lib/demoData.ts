import type {
  AnalysisResult,
  ApplicationRecord,
  PaymentPlan,
  ReportSummary,
  UploadedDocument,
  User,
} from "@/types";

export const demoCustomer: User = {
  id: "customer-deniz-kaya",
  fullName: "Deniz Kaya",
  role: "customer",
  title: "Premium müşteri",
};

export const demoExpert: User = {
  id: "expert-ahmet-uzman",
  fullName: "Ahmet Uzman",
  role: "expert",
  title: "Kredi risk uzmanı",
};

export const initialDocuments: UploadedDocument[] = [
  { id: "identity", name: "Kimlik Belgesi", type: "Kimlik", status: "bekliyor", progress: 0 },
  { id: "income", name: "Gelir Belgesi", type: "Maaş / SGK", status: "bekliyor", progress: 0 },
  { id: "bank", name: "Banka Hesap Dökümü", type: "Hesap hareketleri", status: "bekliyor", progress: 0 },
  { id: "kvkk", name: "KVKK Onayı", type: "Onay belgesi", status: "bekliyor", progress: 0 },
];

export const demoApplications: ApplicationRecord[] = [
  {
    application_id: "APP-DENIZ-2026-001",
    customer_name: "Deniz Kaya",
    status: "Uzman incelemesinde",
    risk_score: 72,
    risk_level: "Orta",
    document_confidence_score: 0.95,
    consistency_score: 0.82,
    anomaly_score: 0.25,
    ai_recommendation: "Banka uzmanı tarafından manuel inceleme önerilir.",
    expert_decision: "Beklemede",
  },
  {
    application_id: "APP-ZEYNEP-2026-002",
    customer_name: "Zeynep Arslan",
    status: "Ön onaya uygun",
    risk_score: 34,
    risk_level: "Düşük",
    document_confidence_score: 0.91,
    consistency_score: 0.88,
    anomaly_score: 0.08,
    ai_recommendation: "Düşük riskli başvuru. Banka politikasıyla uyumluysa onaylanabilir.",
    expert_decision: "Beklemede",
  },
  {
    application_id: "APP-SEDA-2026-003",
    customer_name: "Seda Acar",
    status: "Detaylı inceleme",
    risk_score: 88,
    risk_level: "Yüksek",
    document_confidence_score: 0.73,
    consistency_score: 0.58,
    anomaly_score: 0.52,
    ai_recommendation: "Ek belge ve detaylı gelir doğrulaması önerilir.",
    expert_decision: "Beklemede",
  },
];

export const demoAnalysisResult: AnalysisResult = {
  applicationId: "APP-DENIZ-2026-001",
  eligibilityScore: 78,
  riskScore: 72,
  riskLevel: "Orta",
  documentConfidenceScore: 0.95,
  consistencyScore: 0.82,
  anomalyScore: 0.25,
  aiRecommendation: "AI önerisi: başvuru banka uzmanı tarafından manuel incelemeye alınmalı.",
  summary: "Belgeler okunabilir, gelir doğrulaması büyük ölçüde tutarlı. Harcama/gelir oranı uzman incelemesi gerektiriyor.",
  reasons: [
    "Kimlik, gelir belgesi ve banka dökümü arasında temel bilgiler uyumlu.",
    "Banka maaş girişleri beyan edilen gelirle yakın seviyede.",
    "Harcama/gelir oranı yüksek olduğu için nihai karar banka uzmanına bırakılmalı.",
  ],
};

export const demoPaymentPlan: PaymentPlan = {
  loan_id: "LOAN-DENIZ-001",
  approved_amount: 200000,
  monthly_payment: 7950,
  maturity_months: 36,
  remaining_principal: 163420,
  installments: [
    { installment_no: 7, due_date: "2026-06-15", amount: 7950, status: "Gecikmiş" },
    { installment_no: 8, due_date: "2026-07-15", amount: 7950, status: "Yaklaşıyor" },
    { installment_no: 9, due_date: "2026-08-15", amount: 7950, status: "Planlandı" },
    { installment_no: 6, due_date: "2026-05-15", amount: 7950, status: "Ödendi" },
  ],
};

export const demoReports: ReportSummary[] = [
  { id: "RPT-001", title: "Aylık Başvuru Risk Dağılımı", type: "Risk raporu", createdAt: "2026-05-14" },
  { id: "RPT-002", title: "Belge Güven Skoru Özeti", type: "Belge raporu", createdAt: "2026-05-14" },
  { id: "RPT-003", title: "Uzman Karar Süreci Analizi", type: "Operasyon raporu", createdAt: "2026-05-13" },
];
