import { apiRequest } from "@/lib/apiClient";
import { demoAnalysisResult } from "@/lib/demoData";
import { endpoints } from "@/lib/endpoints";
import type { AnalysisResult, ApplicationForm, UploadedDocument } from "@/types";
import { mapAnalysisResult } from "./mappers";

export async function startAnalysis(form: ApplicationForm, documents: UploadedDocument[]): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append("application_form", JSON.stringify(form));
  formData.append("use_dataset_summary", "true");
  formData.append("create_report", "true");
  formData.append("save_application", "true");

  documents
    .filter((document) => document.file)
    .forEach((document) => {
      formData.append("documents", document.file as File);
    });

  const response = await apiRequest<unknown>(endpoints.analyze, {
    method: "POST",
    body: formData,
  });

  if (!response.data) {
    return demoAnalysisResult;
  }

  return mapAnalysisResult(response.data);
}

export async function getAnalysisStatus() {
  return { status: "completed" };
}

export async function getAnalysisResult(): Promise<AnalysisResult> {
  return demoAnalysisResult;
}
