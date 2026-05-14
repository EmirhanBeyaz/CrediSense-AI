import { apiRequest } from "@/lib/apiClient";
import { demoPaymentPlan } from "@/lib/demoData";
import { endpoints } from "@/lib/endpoints";
import type { PaymentPlan } from "@/types";
import { mapPaymentPlan } from "./mappers";

export async function getApprovedLoanPlan(): Promise<PaymentPlan> {
  const response = await apiRequest<unknown>(endpoints.myPaymentPlan);
  if (!response.data) {
    return demoPaymentPlan;
  }
  return mapPaymentPlan(response.data);
}
