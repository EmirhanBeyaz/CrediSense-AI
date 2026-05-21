import { apiRequest } from "@/lib/apiClient";
import { endpoints } from "@/lib/endpoints";
import type { PaymentPlan, Wallet } from "@/types";
import { mapPaymentPlan, mapWallet } from "./mappers";

export type WalletTopUpInput = {
  amount: number;
  card_number: string;
  expiry_date: string;
  cvv: string;
  cardholder_name: string;
};

export async function getApprovedLoanPlan(): Promise<PaymentPlan | null> {
  const response = await apiRequest<unknown>(endpoints.myPaymentPlan);
  if (!response.data) {
    return null;
  }
  return mapPaymentPlan(response.data);
}

export async function getWallet(): Promise<Wallet> {
  const response = await apiRequest<unknown>(endpoints.wallet);
  if (!response.data) {
    return { balance: 0, currency: "TRY", transactions: [] };
  }
  return mapWallet(response.data);
}

export async function topUpWallet(input: WalletTopUpInput): Promise<Wallet> {
  const response = await apiRequest<unknown>(endpoints.walletTopUp, {
    method: "POST",
    body: input,
  });

  if (!response.data) {
    throw new Error(response.error || "Cüzdan bakiyesi yüklenemedi.");
  }

  return mapWallet(response.data);
}

export async function payInstallmentFromWallet(
  loanId: string,
  installmentNo: number,
): Promise<{ paymentPlan: PaymentPlan; wallet: Wallet }> {
  const response = await apiRequest<{ payment_plan: unknown; wallet: unknown }>(endpoints.installmentPay(loanId, installmentNo), {
    method: "POST",
    body: {
      note: "Müşteri cüzdan bakiyesi ile ödeme",
    },
  });

  if (!response.data) {
    throw new Error(response.error || "Taksit cüzdan bakiyesiyle ödenemedi.");
  }

  return {
    paymentPlan: mapPaymentPlan(response.data.payment_plan),
    wallet: mapWallet(response.data.wallet),
  };
}

export async function payRemainingPrincipalFromWallet(loanId: string): Promise<{ paymentPlan: PaymentPlan; wallet: Wallet }> {
  const response = await apiRequest<{ payment_plan: unknown; wallet: unknown }>(endpoints.principalPayoff(loanId), {
    method: "POST",
    body: {
      note: "Müşteri kalan ana parayı cüzdan bakiyesi ile faizsiz kapattı",
    },
  });

  if (!response.data) {
    throw new Error(response.error || "Kalan ana para cüzdan bakiyesiyle kapatılamadı.");
  }

  return {
    paymentPlan: mapPaymentPlan(response.data.payment_plan),
    wallet: mapWallet(response.data.wallet),
  };
}
