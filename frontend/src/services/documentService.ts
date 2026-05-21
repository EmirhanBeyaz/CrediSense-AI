import { apiRequest } from "@/lib/apiClient";
import { endpoints } from "@/lib/endpoints";
import type { ApplicationForm, UploadedDocument } from "@/types";

type ApiDocument = {
  document_id: string;
  document_type: string;
  document_name: string;
  original_file_name: string;
  status: string;
  extracted_form_fields?: Partial<ApplicationForm>;
};

export async function uploadDocument(document: UploadedDocument, file: File): Promise<UploadedDocument> {
  const formData = new FormData();
  formData.append("document", file);
  formData.append("document_type", document.id);
  formData.append("document_name", document.name);

  const response = await apiRequest<ApiDocument>(endpoints.documents, {
    method: "POST",
    body: formData,
  });

  if (!response.data) {
    return {
      ...document,
      file,
      status: "yuklendi",
      progress: 100,
    };
  }

  return {
    ...document,
    id: response.data.document_type || document.id,
    name: response.data.document_name || document.name,
    file,
    status: response.data.status === "uploaded" ? "yuklendi" : document.status,
    progress: 100,
    extractedFields: response.data.extracted_form_fields || {},
  };
}

export async function getDocuments(documents: UploadedDocument[]): Promise<UploadedDocument[]> {
  const response = await apiRequest<{ documents: ApiDocument[] }>(endpoints.documents);
  if (!response.data) {
    return documents;
  }

  const savedTypes = new Set(response.data.documents.map((document) => document.document_type));
  return documents.map((document) =>
    savedTypes.has(document.id)
      ? {
          ...document,
          status: "yuklendi",
          progress: 100,
        }
      : document,
  );
}
