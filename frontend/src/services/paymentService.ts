import { apiRequest } from "@/lib/apiClient";
import { endpoints } from "@/lib/endpoints";
import type { PaymentPlan } from "@/types";
import { mapPaymentPlan } from "./mappers";

export async function getApprovedLoanPlan(): Promise<PaymentPlan | null> {
  const response = await apiRequest<unknown>(endpoints.myPaymentPlan);
  if (!response.data) {
    return null;
  }
  return mapPaymentPlan(response.data);
}
