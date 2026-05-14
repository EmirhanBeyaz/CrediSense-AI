import { apiRequest } from "@/lib/apiClient";
import { demoApplications } from "@/lib/demoData";
import { endpoints } from "@/lib/endpoints";
import type { ApplicationRecord } from "@/types";
import { mapApplicationRecord } from "./mappers";

export async function getExpertApplications(): Promise<ApplicationRecord[]> {
  const response = await apiRequest<{ applications: unknown[] }>(endpoints.applications);
  if (!response.data) {
    return demoApplications;
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

export async function approveApplication(applicationId: string, note = "") {
  return sendDecision(applicationId, "approve", note);
}

export async function reviseApplication(applicationId: string, note = "") {
  return sendDecision(applicationId, "send_to_deep_review", note);
}

export async function requestExtraDocument(applicationId: string, requestedDocuments: string[], note = "") {
  return sendDecision(applicationId, "request_extra_document", note, requestedDocuments);
}

export async function rejectApplication(applicationId: string, note = "") {
  return sendDecision(applicationId, "reject", note);
}

async function sendDecision(applicationId: string, decisionType: string, note: string, requestedDocuments: string[] = []) {
  const response = await apiRequest<unknown>(endpoints.decision(applicationId), {
    method: "POST",
    body: {
      decision_type: decisionType,
      note,
      actor: "bank_expert",
      requested_documents: requestedDocuments,
    },
  });

  if (!response.data) {
    return {
      ...demoApplications.find((item) => item.application_id === applicationId),
      expert_decision: decisionType,
      status: "Karar işlendi",
    };
  }

  return mapApplicationRecord(response.data);
}
