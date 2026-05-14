import { apiRequest } from "@/lib/apiClient";
import { endpoints } from "@/lib/endpoints";
import { demoApplications } from "@/lib/demoData";
import type { ApplicationForm, ApplicationRecord, UploadedDocument } from "@/types";
import { mapApplicationRecord } from "./mappers";

export async function createApplication(form: ApplicationForm, documents: UploadedDocument[]) {
  return {
    application_id: `LOCAL-${Date.now()}`,
    customer_name: form.full_name,
    status: documents.some((document) => document.status === "yuklendi") ? "Belgeler yüklendi" : "Taslak",
  };
}

export async function getCustomerApplications(): Promise<ApplicationRecord[]> {
  const response = await apiRequest<{ applications: unknown[] }>(endpoints.applications);
  if (!response.data) {
    return demoApplications;
  }
  return response.data.applications.map(mapApplicationRecord);
}

export async function getApplicationDetail(applicationId: string): Promise<ApplicationRecord> {
  const response = await apiRequest<unknown>(endpoints.applicationDetail(applicationId));
  if (!response.data) {
    return demoApplications.find((item) => item.application_id === applicationId) || demoApplications[0];
  }
  return mapApplicationRecord(response.data);
}
