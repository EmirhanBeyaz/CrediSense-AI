import { apiRequest } from "@/lib/apiClient";
import { endpoints } from "@/lib/endpoints";

type AssistantResponse = {
  answer?: string;
  message?: string;
  response?: string;
};

export async function sendAssistantMessage(loanId: string, message: string): Promise<string> {
  const response = await apiRequest<AssistantResponse>(endpoints.assistant(loanId), {
    method: "POST",
    body: {
      message,
    },
  });

  if (!response.data) {
    throw new Error(response.error || "AI finans asistanı cevabı alınamadı.");
  }

  return response.data.answer || response.data.response || response.data.message || fallbackAnswer(message);
}

function fallbackAnswer(message: string): string {
  const normalized = message.toLocaleLowerCase("tr-TR");
  if (normalized.includes("aylık") || normalized.includes("taksit")) {
    return "Aylık taksit, vade ve toplam geri ödeme bilgisi ödeme planı ekranındaki banka onaylı plandan alınır.";
  }
  if (normalized.includes("toplam") || normalized.includes("maliyet") || normalized.includes("faiz")) {
    return "Toplam geri ödeme ve faiz bilgisi banka onaylı ödeme planına göre hesaplanır.";
  }
  if (normalized.includes("kalan")) {
    return "Kalan ana para banka onaylı ödeme planından alınır. Net kapama tutarı banka tarafından kesinleştirilmelidir.";
  }
  if (normalized.includes("erken")) {
    return "Erken kapama talebi oluşturabilirsiniz. Nihai kapama tutarı banka onayından sonra kesinleşir.";
  }
  if (normalized.includes("gecik")) {
    return "Gecikme kontrolü ödeme planındaki taksit durumlarına göre yapılır.";
  }
  return "Bu konuda ödeme planınızı inceleyip banka destek talebi oluşturabilirim.";
}
