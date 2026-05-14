"use client";

import { useMemo, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { LoginScreen } from "@/features/auth/LoginScreen";
import { CustomerViews } from "@/features/customer/CustomerViews";
import { ExpertViews } from "@/features/expert/ExpertViews";
import {
  login as loginService,
  logout as logoutService,
  register as registerService,
  verifyEmail as verifyEmailService,
  type RegisterPayload,
} from "@/services/authService";
import type { AppView, CustomerView, ExpertView, Role, User } from "@/types";

const customerTitles: Record<CustomerView, { title: string; subtitle: string }> = {
  "customer-home": {
    title: "Müşteri Ana Paneli",
    subtitle: "Başvuru durumunuzu, belge yüklemelerini ve ödeme planınızı tek yerden takip edin.",
  },
  "new-application": {
    title: "Yeni Başvuru ve Belge Yükleme",
    subtitle: "PDF belgelerinizi yükleyip kredi başvuru formunu tamamlayın.",
  },
  documents: {
    title: "Belgelerim",
    subtitle: "Sisteme yüklediğiniz belgelerin durumunu ve doğrulama sürecini görüntüleyin.",
  },
  "analysis-process": {
    title: "AI Analiz Süreci",
    subtitle: "PDF okuma, belge anlama, tutarlılık ve risk tahmini katmanlarını adım adım izleyin.",
  },
  "analysis-results": {
    title: "Analiz Sonuçlarım",
    subtitle: "Kredi uygunluk skorunu ve açıklanabilir analiz özetini görüntüleyin.",
  },
  "bank-approval": {
    title: "Banka Onayı",
    subtitle: "AI önerisi ile banka onay süreci arasındaki ayrımı takip edin.",
  },
  "payment-plan": {
    title: "Ödeme Planım",
    subtitle: "Onaylanan kredi için taksitleri, kalan borcu ve ödeme durumunu görün.",
  },
  assistant: {
    title: "AI Finans Asistanı",
    subtitle: "Ödeme planı, kalan borç ve erken kapama konularında destek alın.",
  },
  "customer-profile": {
    title: "Profil",
    subtitle: "Kişisel bilgiler ve bildirim tercihleri.",
  },
};

const expertTitles: Record<ExpertView, { title: string; subtitle: string }> = {
  "expert-home": {
    title: "Uzman Paneli",
    subtitle: "Risk, belge ve karar bekleyen başvuruların operasyon özetini görüntüleyin.",
  },
  "application-queue": {
    title: "Başvuru Kuyruğu",
    subtitle: "Banka uzmanı incelemesi bekleyen başvuruları listeleyin.",
  },
  "pending-review": {
    title: "İnceleme Bekleyenler",
    subtitle: "Manuel değerlendirme gerektiren başvurulara odaklanın.",
  },
  "document-control": {
    title: "Belge Kontrolü",
    subtitle: "Belge güven, tutarlılık ve anomali skorlarını inceleyin.",
  },
  "risk-analysis": {
    title: "Risk Analizi",
    subtitle: "AI karar destek skorlarını ve açıklamalarını değerlendirin.",
  },
  "decision-process": {
    title: "Karar Süreci",
    subtitle: "Onay, revize, ek belge ve ret aksiyonlarını backend’e gönderin.",
  },
  reports: {
    title: "Raporlar",
    subtitle: "Operasyon, risk ve belge kalite raporlarını görüntüleyin.",
  },
  "expert-profile": {
    title: "Profil",
    subtitle: "Uzman kullanıcı bilgileri ve yetki ayarları.",
  },
};

export default function Home() {
  const [role, setRole] = useState<Role | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [activeView, setActiveView] = useState<AppView>("customer-home");
  const [loginLoading, setLoginLoading] = useState(false);
  const [toasts, setToasts] = useState<string[]>([]);

  const titleData = useMemo(() => {
    if (role === "expert") {
      return expertTitles[activeView as ExpertView];
    }
    return customerTitles[activeView as CustomerView];
  }, [activeView, role]);

  async function handleLogin(nextRole: Role, identifier: string, password: string) {
    setLoginLoading(true);
    try {
      const nextUser = await loginService(nextRole, identifier, password);
      setRole(nextUser.role);
      setUser(nextUser);
      setActiveView(nextUser.role === "expert" ? "expert-home" : "customer-home");
      showToast(nextUser.role === "expert" ? "Banka uzman paneli açıldı." : "Müşteri paneli açıldı.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Giriş yapılamadı.");
    } finally {
      setLoginLoading(false);
    }
  }

  async function handleRegister(payload: RegisterPayload) {
    setLoginLoading(true);
    try {
      const result = await registerService(payload);
      showToast(result.email_sent ? "Dogrulama e-postasi gonderildi." : "SMTP ayari olmadigi icin yerel dogrulama tokeni gosterildi.");
      return {
        message: result.message || "Dogrulama tokeni e-posta adresinize gonderildi.",
        developmentToken: result.development_token,
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : "Kayit olusturulamadi.";
      showToast(message);
      throw error;
    } finally {
      setLoginLoading(false);
    }
  }

  async function handleVerifyEmail(identifier: string, token: string) {
    setLoginLoading(true);
    try {
      const nextUser = await verifyEmailService(identifier, token);
      setRole(nextUser.role);
      setUser(nextUser);
      setActiveView(nextUser.role === "expert" ? "expert-home" : "customer-home");
      showToast("E-posta dogrulandi ve oturum acildi.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "E-posta dogrulanamadi.");
    } finally {
      setLoginLoading(false);
    }
  }

  function handleLogout() {
    logoutService();
    setRole(null);
    setUser(null);
    setActiveView("customer-home");
    showToast("Oturum kapatıldı.");
  }

  function showToast(message: string) {
    setToasts((items) => [...items, message]);
    window.setTimeout(() => {
      setToasts((items) => items.slice(1));
    }, 3200);
  }

  if (!role || !user) {
    return (
      <>
        <LoginScreen
          loading={loginLoading}
          onLogin={handleLogin}
          onRegister={handleRegister}
          onVerifyEmail={handleVerifyEmail}
        />
        <ToastHost toasts={toasts} />
      </>
    );
  }

  return (
    <>
      <AppShell
        activeView={activeView}
        onLogout={handleLogout}
        onNavigate={setActiveView}
        role={role}
        subtitle={titleData.subtitle}
        title={titleData.title}
        user={user}
      >
        {role === "expert" ? (
          <ExpertViews activeView={activeView as ExpertView} showToast={showToast} />
        ) : (
          <CustomerViews activeView={activeView as CustomerView} onNavigate={(view) => setActiveView(view)} showToast={showToast} user={user} />
        )}
      </AppShell>
      <ToastHost toasts={toasts} />
    </>
  );
}

function ToastHost({ toasts }: { toasts: string[] }) {
  return (
    <div className="fixed bottom-5 right-5 z-50 grid w-[min(380px,calc(100vw-40px))] gap-3">
      {toasts.map((toast, index) => (
        <div className="rounded-xl border border-primary/30 bg-surface/90 p-4 text-sm shadow-glow backdrop-blur-xl" key={`${toast}-${index}`}>
          {toast}
        </div>
      ))}
    </div>
  );
}
