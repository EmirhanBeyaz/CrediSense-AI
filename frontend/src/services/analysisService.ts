import { apiRequest } from "@/lib/apiClient";
import { endpoints } from "@/lib/endpoints";
import type { AnalysisResult, ApplicationForm, UploadedDocument } from "@/types";
import { mapAnalysisResult } from "./mappers";

export async function startAnalysis(form: ApplicationForm, documents: UploadedDocument[]): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append("application_form", JSON.stringify(form));
  formData.append("use_dataset_summary", "true");
  formData.append("create_report", "true");
  formData.append("save_application", "true");

  const uploadedDocuments = documents.filter((document) => document.file);

  uploadedDocuments.forEach((document) => {
    formData.append("documents", document.file as File);
    formData.append("document_types", document.id);
    formData.append("document_names", document.name);
  });

  const response = await apiRequest<unknown>(endpoints.analyze, {
    method: "POST",
    body: formData,
  });

  if (!response.data) {
    throw new Error(response.error || "Analiz sonucu alinamadi.");
  }

  return mapAnalysisResult(response.data);
}

export async function getAnalysisStatus() {
  return { status: "completed" };
}

export async function getAnalysisResult(): Promise<AnalysisResult> {
  throw new Error("Analiz sonucu sadece backend analizinden sonra alinabilir.");
}
