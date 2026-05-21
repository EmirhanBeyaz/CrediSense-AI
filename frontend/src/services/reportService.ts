import { apiRequest } from "@/lib/apiClient";
import { endpoints } from "@/lib/endpoints";
import type { ReportSummary } from "@/types";

type ApiReport = {
  report_id: string;
  application_id: string;
  title?: string;
  report_type?: string;
  content?: string;
  customer_name?: string;
  created_at: string;
  report_files?: {
    json_report?: string;
    markdown_report?: string;
  };
};

export async function getReports(): Promise<ReportSummary[]> {
  const response = await apiRequest<{ reports: ApiReport[] }>(endpoints.reports);
  if (!response.data) {
    throw new Error(response.error || "Rapor listesi alınamadı.");
  }

  return response.data.reports.map((report) => ({
    id: report.report_id,
    applicationId: report.application_id,
    title: report.title || `Başvuru raporu ${report.application_id}`,
    type: report.report_type || (report.report_files?.markdown_report ? "Markdown" : "JSON"),
    createdAt: report.created_at,
    customerName: report.customer_name,
    content: report.content,
  }));
}
