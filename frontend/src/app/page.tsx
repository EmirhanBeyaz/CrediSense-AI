"use client";

import { useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { LoginScreen } from "@/features/auth/LoginScreen";
import { CustomerViews } from "@/features/customer/CustomerViews";
import { ExpertViews } from "@/features/expert/ExpertViews";
import { getAuthToken } from "@/lib/apiClient";
import {
  deleteCurrentAccount as deleteCurrentAccountService,
  forgotPassword as forgotPasswordService,
  getCurrentUser,
  login as loginService,
  logout as logoutService,
  register as registerService,
  resetPassword as resetPasswordService,
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
  "customer-settings": {
    title: "Ayarlar",
    subtitle: "Hesap, oturum ve uygulama tercihlerinizi yönetin.",
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
    subtitle: "",
  },
  reports: {
    title: "Raporlar",
    subtitle: "Operasyon, risk ve belge kalite raporlarını görüntüleyin.",
  },
  "expert-profile": {
    title: "Profil",
    subtitle: "Uzman kullanıcı bilgileri ve yetki ayarları.",
  },
  "expert-settings": {
    title: "Ayarlar",
    subtitle: "Uzman paneli tercihleri ve oturum ayarları.",
  },
};

const ACTIVE_VIEW_STORAGE_KEY = "credisense_active_view";

const customerViews = new Set<AppView>([
  "customer-home",
  "new-application",
  "documents",
  "analysis-process",
  "analysis-results",
  "bank-approval",
  "payment-plan",
  "assistant",
  "customer-profile",
  "customer-settings",
]);

const expertViews = new Set<AppView>([
  "expert-home",
  "application-queue",
  "pending-review",
  "document-control",
  "risk-analysis",
  "decision-process",
  "reports",
  "expert-profile",
  "expert-settings",
]);

export default function Home() {
  const [role, setRole] = useState<Role | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [activeView, setActiveView] = useState<AppView>("customer-home");
  const [loginLoading, setLoginLoading] = useState(false);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [toasts, setToasts] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      if (!getAuthToken()) {
        setSessionLoading(false);
        return;
      }

      try {
        const nextUser = await getCurrentUser();
        if (cancelled) return;

        setRole(nextUser.role);
        setUser(nextUser);
        setActiveView(readStoredView(nextUser.role));
      } catch {
        logoutService();
        clearStoredView();
      } finally {
        if (!cancelled) {
          setSessionLoading(false);
        }
      }
    }

    restoreSession();
    return () => {
      cancelled = true;
    };
  }, []);

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
      setView(defaultViewForRole(nextUser.role));
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
      setView(defaultViewForRole(nextUser.role));
      showToast("E-posta dogrulandi ve oturum acildi.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "E-posta dogrulanamadi.");
    } finally {
      setLoginLoading(false);
    }
  }

  async function handleForgotPassword(nextRole: Role, email: string) {
    setLoginLoading(true);
    try {
      const result = await forgotPasswordService(nextRole, email);
      showToast(result.email_sent ? "Şifre sıfırlama kodu e-postaya gönderildi." : "SMTP ayarı olmadığı için yerel şifre sıfırlama kodu gösterildi.");
      return {
        message: result.message || "Şifre sıfırlama kodu e-posta adresinize gönderildi.",
        developmentToken: result.development_token,
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : "Şifre sıfırlama kodu gönderilemedi.";
      showToast(message);
      throw error;
    } finally {
      setLoginLoading(false);
    }
  }

  async function handleResetPassword(nextRole: Role, email: string, token: string, newPassword: string) {
    setLoginLoading(true);
    try {
      await resetPasswordService(nextRole, email, token, newPassword);
      showToast("Şifre güncellendi. Yeni şifreyle giriş yapabilirsiniz.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Şifre güncellenemedi.");
      throw error;
    } finally {
      setLoginLoading(false);
    }
  }

  function handleLogout() {
    logoutService();
    clearStoredView();
    setRole(null);
    setUser(null);
    setActiveView("customer-home");
    showToast("Oturum kapatıldı.");
  }

  async function handleDeleteAccount() {
    try {
      await deleteCurrentAccountService();
      clearStoredView();
      setRole(null);
      setUser(null);
      setActiveView("customer-home");
      showToast("Hesabınız silindi.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Hesap silinemedi.");
    }
  }

  function showToast(message: string) {
    setToasts((items) => [...items, message]);
    window.setTimeout(() => {
      setToasts((items) => items.slice(1));
    }, 3200);
  }

  function setView(view: AppView) {
    setActiveView(view);
    storeView(view);
  }

  if (sessionLoading) {
    return (
      <main className="grid min-h-screen place-items-center bg-background px-6 text-center">
        <div className="glass-panel rounded-2xl p-8">
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">CrediSense AI</p>
          <h1 className="mt-3 font-display text-2xl font-bold">Oturum kontrol ediliyor</h1>
        </div>
      </main>
    );
  }

  if (!role || !user) {
    return (
      <>
        <LoginScreen
          loading={loginLoading}
          onForgotPassword={handleForgotPassword}
          onLogin={handleLogin}
          onRegister={handleRegister}
          onResetPassword={handleResetPassword}
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
        onNavigate={setView}
        role={role}
        subtitle={titleData.subtitle}
        title={titleData.title}
        user={user}
      >
        {role === "expert" ? (
          <ExpertViews activeView={activeView as ExpertView} onUserUpdate={setUser} showToast={showToast} user={user} />
        ) : (
          <CustomerViews
            activeView={activeView as CustomerView}
            onAccountDeleted={handleDeleteAccount}
            onNavigate={(view) => setView(view)}
            onUserUpdate={setUser}
            showToast={showToast}
            user={user}
          />
        )}
      </AppShell>
      <ToastHost toasts={toasts} />
    </>
  );
}

function defaultViewForRole(role: Role): AppView {
  return role === "expert" ? "expert-home" : "customer-home";
}

function readStoredView(role: Role): AppView {
  if (typeof window === "undefined") {
    return defaultViewForRole(role);
  }

  const storedView = window.localStorage.getItem(ACTIVE_VIEW_STORAGE_KEY) as AppView | null;
  if (storedView && isViewAllowedForRole(storedView, role)) {
    return storedView;
  }
  return defaultViewForRole(role);
}

function storeView(view: AppView) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(ACTIVE_VIEW_STORAGE_KEY, view);
  }
}

function clearStoredView() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(ACTIVE_VIEW_STORAGE_KEY);
  }
}

function isViewAllowedForRole(view: AppView, role: Role) {
  return role === "expert" ? expertViews.has(view) : customerViews.has(view);
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
