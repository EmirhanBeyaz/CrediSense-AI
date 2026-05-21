export type Role = "customer" | "expert";

export type CustomerView =
  | "customer-home"
  | "new-application"
  | "documents"
  | "analysis-process"
  | "analysis-results"
  | "bank-approval"
  | "payment-plan"
  | "assistant"
  | "customer-profile"
  | "customer-settings";

export type ExpertView =
  | "expert-home"
  | "application-queue"
  | "pending-review"
  | "document-control"
  | "risk-analysis"
  | "decision-process"
  | "reports"
  | "expert-profile"
  | "expert-settings";

export type AppView = CustomerView | ExpertView;

export type User = {
  id: string;
  username?: string;
  email?: string;
  emailVerified?: boolean;
  fullName: string;
  role: Role;
  title: string;
  profile?: {
    profile_image?: string;
    test_id?: string;
    birth_date?: string;
    employer?: string;
    declared_income?: string;
    requested_credit?: string;
    maturity_months?: string;
    existing_debt?: string;
    current_debt?: number;
    active_loan_id?: string;
    active_application_id?: string;
    wallet_balance?: number;
    monthly_interest_rate?: number;
    annual_interest_rate?: number;
    [key: string]: unknown;
  };
};

export type UploadedDocument = {
  id: string;
  name: string;
  type: string;
  status: "bekliyor" | "yuklendi" | "inceleniyor" | "onaylandi" | "eksik";
  file?: File;
  progress: number;
  extractedFields?: Partial<ApplicationForm>;
};

export type ApplicationDocument = {
  document_id: string;
  document_type: string;
  document_name: string;
  original_file_name: string;
  status: string;
  created_at?: string;
  application_id?: string;
  view_url?: string;
};

export type ApplicationForm = {
  full_name: string;
  test_id: string;
  birth_date: string;
  employer: string;
  declared_income: string;
  requested_credit: string;
  maturity_months: string;
  existing_debt: string;
};

export type ApplicationRecord = {
  application_id: string;
  customer_name: string;
  status: string;
  status_code?: string;
  created_at?: string;
  risk_score?: number;
  risk_level?: string;
  document_confidence_score?: number;
  consistency_score?: number;
  anomaly_score?: number;
  ai_recommendation?: string;
  expert_decision?: string;
  review_route?: "auto_pre_approved" | "manual_review" | "deep_review" | "completed";
  review_route_text?: string;
  system_action?: string;
  requested_documents?: string[];
  documents?: ApplicationDocument[];
  decision_note?: string;
  report_count?: number;
  credit_request?: {
    requested_amount?: number | string;
    term_months?: number | string;
    declared_monthly_income?: number | string;
    current_total_debt?: number | string;
    [key: string]: unknown;
  };
  reasons?: string[];
  raw?: unknown;
};

export type AnalysisStageStatus = "bekliyor" | "calisiyor" | "tamamlandi" | "hata";

export type AnalysisStage = {
  id: string;
  title: string;
  description: string;
  status: AnalysisStageStatus;
  errorMessage?: string;
};

export type AnalysisResult = {
  applicationId: string;
  eligibilityScore: number;
  riskScore: number;
  riskLevel: string;
  documentConfidenceScore: number;
  consistencyScore: number;
  anomalyScore: number;
  aiRecommendation: string;
  summary: string;
  reasons: string[];
  raw?: unknown;
};

export type PaymentPlan = {
  loan_id: string;
  approved_amount: number;
  monthly_payment: number;
  maturity_months: number;
  remaining_principal: number;
  monthly_interest_rate: number;
  annual_interest_rate: number;
  total_payment: number;
  total_interest: number;
  interest_policy?: {
    min_monthly_interest_rate?: number;
    max_monthly_interest_rate?: number;
    assigned_monthly_interest_rate?: number;
    effective_monthly_interest_rate?: number;
    rate_source?: string;
    reason?: string;
  };
  installments: Array<{
    installment_no: number;
    due_date: string;
    amount: number;
    status: string;
    paid_date?: string;
  }>;
};

export type WalletTransaction = {
  transaction_id: string;
  type: string;
  amount: number;
  currency: string;
  description?: string;
  created_at?: string;
  loan_id?: string;
  installment_no?: number;
  card_last4?: string;
};

export type Wallet = {
  balance: number;
  currency: string;
  transactions: WalletTransaction[];
};

export type ReportSummary = {
  id: string;
  title: string;
  type: string;
  createdAt: string;
  applicationId?: string;
  content?: string;
};

export type AssistantMessage = {
  id: string;
  sender: "user" | "assistant";
  text: string;
};

export type ApiResult<T> = {
  data: T | null;
  error: string;
  fromFallback: boolean;
};
