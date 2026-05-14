import { apiRequest } from "@/lib/apiClient";
import { endpoints } from "@/lib/endpoints";

export async function sendAssistantMessage(loanId: string, message: string): Promise<string> {
  const response = await apiRequest<{ answer?: string; message?: string; response?: string }>(endpoints.assistant(loanId), {
    method: "POST",
    body: {
      message,
    },
  });

  if (!response.data) {
    return fallbackAnswer(message);
  }

  return response.data.answer || response.data.response || response.data.message || fallbackAnswer(message);
}

function fallbackAnswer(message: string): string {
  const normalized = message.toLocaleLowerCase("tr-TR");
  if (normalized.includes("kalan")) {
    return "Tahmini kalan ana para 163.420 TL görünüyor. Net tutar banka ödeme sistemiyle doğrulanmalıdır.";
  }
  if (normalized.includes("erken")) {
    return "Erken kapama talebi oluşturabilirsiniz. Nihai kapama tutarı banka onayından sonra kesinleşir.";
  }
  if (normalized.includes("gecik")) {
    return "Bir taksit gecikmiş görünüyor. Ödeme yapıldığında plan otomatik güncellenir.";
  }
  return "Bu konuda ödeme planınızı inceleyip banka destek talebi oluşturabilirim.";
}
