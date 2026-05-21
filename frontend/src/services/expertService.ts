import { apiRequest, getAuthToken } from "@/lib/apiClient";
import { demoApplications } from "@/lib/demoData";
import { API_BASE_URL, endpoints } from "@/lib/endpoints";
import type { ApplicationDocument, ApplicationRecord, ReportSummary } from "@/types";
import { mapApplicationRecord } from "./mappers";

type ApplicationScope = "all" | "auto" | "manual" | "pending" | "completed";

export type CreditOfferInput = {
  approved_amount?: number;
  term_months?: number;
  monthly_interest_rate?: number;
};

export async function getExpertApplications(scope: ApplicationScope = "all"): Promise<ApplicationRecord[]> {
  const path = scope === "all" ? endpoints.applications : `${endpoints.applications}?scope=${scope}`;
  const response = await apiRequest<{ applications: unknown[] }>(path);
  if (!response.data) {
    return filterDemoApplications(scope);
  }
  return response.data.applications.map(mapApplicationRecord);
}

export async function getExpertApplicationDetail(applicationId: string): Promise<ApplicationRecord> {
  const response = await apiRequest<unknown>(endpoints.applicationDetail(applicationId));
  if (!response.data) {
    return demoApplications.find((item) => item.application_id === applicationId) || demoApplications[0];
  }
  return mapApplicationRecord(response.data);
}

export async function getApplicationDocuments(applicationId: string): Promise<ApplicationDocument[]> {
  const response = await apiRequest<{ documents: ApplicationDocument[] }>(endpoints.applicationDocuments(applicationId));
  return response.data?.documents || [];
}

export async function getApplicationDocumentBlobUrl(documentId: string): Promise<string> {
  const headers = new Headers();
  const token = getAuthToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${endpoints.documentFile(documentId)}`, { headers });
  if (!response.ok) {
    throw new Error(`Belge görüntülenemedi. HTTP ${response.status}`);
  }

  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

export async function approveApplication(applicationId: string, note = "", creditOffer?: CreditOfferInput): Promise<ApplicationRecord> {
  return sendDecision(applicationId, "approve", note, [], creditOffer);
}

export async function reviseApplication(applicationId: string, note = ""): Promise<ApplicationRecord> {
  return sendDecision(applicationId, "revise", note);
}

export async function requestExtraDocument(applicationId: string, requestedDocuments: string[], note = ""): Promise<ApplicationRecord> {
  return sendDecision(applicationId, "request_extra_document", note, requestedDocuments);
}

export async function rejectApplication(applicationId: string, note = ""): Promise<ApplicationRecord> {
  return sendDecision(applicationId, "reject", note);
}

export async function createExpertReport(applicationId: string, title: string, content: string): Promise<ReportSummary> {
  const response = await apiRequest<{ report: any }>(endpoints.expertReport(applicationId), {
    method: "POST",
    body: { title, content },
  });

  if (!response.data) {
    return {
      id: `RPT-LOCAL-${Date.now()}`,
      applicationId,
      title,
      type: "Uzman kanaat raporu",
      createdAt: new Date().toISOString(),
      content,
    };
  }

  return {
    id: response.data.report.report_id,
    applicationId: response.data.report.application_id,
    title: response.data.report.title,
    type: response.data.report.report_type,
    createdAt: response.data.report.created_at,
    content: response.data.report.content,
  };
}

async function sendDecision(
  applicationId: string,
  decisionType: string,
  note: string,
  requestedDocuments: string[] = [],
  creditOffer?: CreditOfferInput,
): Promise<ApplicationRecord> {
  const response = await apiRequest<unknown>(endpoints.decision(applicationId), {
    method: "POST",
    body: {
      decision_type: decisionType,
      note,
      actor: "bank_expert",
      requested_documents: requestedDocuments,
      credit_offer: creditOffer,
    },
  });

  if (!response.data) {
    throw new Error(response.error || "Karar backend'e gonderilemedi.");
  }

  return mapApplicationRecord(response.data);
}

function filterDemoApplications(scope: ApplicationScope) {
  if (scope === "auto") {
    return demoApplications.filter((item) => item.risk_level === "Düşük");
  }
  if (scope === "manual" || scope === "pending") {
    return demoApplications.filter((item) => item.risk_level !== "Düşük");
  }
  if (scope === "completed") {
    return [];
  }
  return demoApplications;
}
