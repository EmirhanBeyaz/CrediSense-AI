"use client";

import { useEffect, useRef, useState, type Dispatch, type SetStateAction, type UIEvent } from "react";
import { Card } from "@/components/ui/Card";
import { ChartCard } from "@/components/ui/ChartCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { ProfileAvatar } from "@/components/ui/ProfileAvatar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Stepper } from "@/components/ui/Stepper";
import { UploadCard } from "@/components/ui/UploadCard";
import { initialDocuments } from "@/lib/demoData";
import { formatCurrency, scorePercent } from "@/lib/format";
import { fileToProfileImage } from "@/lib/profileImage";
import { startAnalysis as startBackendAnalysis } from "@/services/analysisService";
import { getCustomerApplications } from "@/services/applicationService";
import { updateCurrentProfile } from "@/services/authService";
import { getDocuments, uploadDocument } from "@/services/documentService";
import { getApprovedLoanPlan, getWallet, payInstallmentFromWallet, payRemainingPrincipalFromWallet, topUpWallet, type WalletTopUpInput } from "@/services/paymentService";
import { sendAssistantMessage } from "@/services/assistantService";
import type {
  AnalysisResult,
  AnalysisStage,
  ApplicationRecord,
  ApplicationForm,
  AssistantMessage,
  CustomerView,
  PaymentPlan,
  UploadedDocument,
  User,
  Wallet,
} from "@/types";

type CustomerViewsProps = {
  activeView: CustomerView;
  onAccountDeleted: () => Promise<void>;
  onNavigate: (view: CustomerView) => void;
  onUserUpdate: (user: User) => void;
  showToast: (message: string) => void;
  user: User;
};

const defaultForm: ApplicationForm = {
  full_name: "Deniz Kaya",
  test_id: "11111111110",
  birth_date: "12.04.1992",
  employer: "Nova Veri Teknolojileri A.Ş.",
  declared_income: "42.350 TL",
  requested_credit: "300.000 TL",
  maturity_months: "36",
  existing_debt: "153.000 TL",
};

const editableFormFields = new Set<keyof ApplicationForm>(["requested_credit", "maturity_months"]);
const formFieldOrder: Array<keyof ApplicationForm> = [
  "full_name",
  "test_id",
  "birth_date",
  "employer",
  "declared_income",
  "existing_debt",
  "requested_credit",
  "maturity_months",
];

const baseStages: AnalysisStage[] = [
  { id: "pdf", title: "PDF Okuma", description: "Yüklenen belgelerden metin çıkarılır.", status: "bekliyor" },
  { id: "understanding", title: "Belge Anlama", description: "Kimlik, gelir ve banka dökümü alanları ayrıştırılır.", status: "bekliyor" },
  { id: "consistency", title: "Tutarlılık", description: "Belgeler ve form verileri karşılaştırılır.", status: "bekliyor" },
  { id: "features", title: "Finansal Özellikler", description: "Gelir, harcama ve nakit akışı özellikleri hesaplanır.", status: "bekliyor" },
  { id: "risk", title: "Risk Tahmini", description: "Karar destek skoru üretilir.", status: "bekliyor" },
];

export function CustomerViews({ activeView, onAccountDeleted, onNavigate, onUserUpdate, showToast, user }: CustomerViewsProps) {
  const [applicationDocuments, setApplicationDocuments] = useState<UploadedDocument[]>(() => createDocumentPackage());
  const [savedDocuments, setSavedDocuments] = useState<UploadedDocument[]>(() => createDocumentPackage());
  const [form, setForm] = useState<ApplicationForm>(() => buildDefaultForm(user));
  const [stages, setStages] = useState<AnalysisStage[]>(baseStages);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [customerApplications, setCustomerApplications] = useState<ApplicationRecord[]>([]);
  const [latestApplication, setLatestApplication] = useState<ApplicationRecord | null>(null);
  const [selectedApplicationId, setSelectedApplicationId] = useState("");
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisMessage, setAnalysisMessage] = useState("");
  const [kvkkAccepted, setKvkkAccepted] = useState(false);
  const [paymentPlan, setPaymentPlan] = useState<PaymentPlan | null>(null);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [walletActionLoading, setWalletActionLoading] = useState(false);
  const [profileImageLoading, setProfileImageLoading] = useState(false);
  const [assistantMessages, setAssistantMessages] = useState<AssistantMessage[]>(() => [
    buildAssistantGreeting(user),
  ]);

  const previousViewRef = useRef<CustomerView>(activeView);

  const requiredDocumentsReady = applicationDocuments.every((document) => document.file);
  const applicationReady = requiredDocumentsReady && kvkkAccepted;

  useEffect(() => {
    refreshCustomerData();
  }, []);

  useEffect(() => {
    setAssistantMessages((items) => {
      const nextGreeting = buildAssistantGreeting(user, paymentPlan, wallet);
      if (!items.length) {
        return [nextGreeting];
      }
      if (items[0].id !== nextGreeting.id) {
        return items;
      }
      return [nextGreeting, ...items.slice(1)];
    });
  }, [user.fullName, paymentPlan?.loan_id, paymentPlan?.monthly_payment, paymentPlan?.remaining_principal, wallet?.balance]);

  useEffect(() => {
    if (["customer-home", "documents", "bank-approval", "payment-plan", "assistant", "customer-profile"].includes(activeView)) {
      refreshCustomerData();
    }
  }, [activeView]);

  useEffect(() => {
    if (activeView === "new-application" && previousViewRef.current !== "new-application") {
      setApplicationDocuments(createDocumentPackage());
      setKvkkAccepted(false);
      setStages(baseStages);
      setAnalysisMessage("");
      setAnalysisResult(null);
    }

    previousViewRef.current = activeView;
  }, [activeView]);

  async function refreshCustomerData() {
    const [documentResult, applicationResult, paymentResult, walletResult] = await Promise.allSettled([
      getDocuments(createDocumentPackage()),
      getCustomerApplications(),
      getApprovedLoanPlan(),
      getWallet(),
    ]);

    const nextApplications = applicationResult.status === "fulfilled" ? applicationResult.value : [];
    const latest = nextApplications[0] || null;
    const nextDocuments = documentResult.status === "fulfilled" ? documentResult.value : createDocumentPackage();

    setCustomerApplications(nextApplications);
    setLatestApplication(latest);
    setSelectedApplicationId((currentId) =>
      nextApplications.some((application) => application.application_id === currentId)
        ? currentId
        : latest?.application_id || "",
    );
    setSavedDocuments(mergeRequestedDocuments(nextDocuments, latest?.requested_documents || []));
    setPaymentPlan(paymentResult.status === "fulfilled" ? paymentResult.value : null);
    setWallet(walletResult.status === "fulfilled" ? walletResult.value : { balance: 0, currency: "TRY", transactions: [] });
  }

  async function handleApplicationUpload(documentId: string, file: File) {
    const target = applicationDocuments.find((document) => document.id === documentId);
    if (!target) return;

    setApplicationDocuments((items) =>
      items.map((document) =>
        document.id === documentId ? { ...document, file, status: "inceleniyor", progress: 55 } : document,
      ),
    );

    try {
      const uploaded = await uploadDocument(target, file);
      setApplicationDocuments((items) => items.map((document) => (document.id === documentId ? uploaded : document)));
      setSavedDocuments((items) => replaceDocumentInPackage(items, uploaded));
      const extractedFormFields = uploaded.extractedFields || {};
      if (Object.keys(extractedFormFields).length) {
        setForm((currentForm) => mergeExtractedFormFields(currentForm, extractedFormFields));
        showToast(`${target.name} yüklendi, form bilgileri belgeden güncellendi.`);
      } else {
        showToast(`${target.name} yüklendi.`);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Belge yuklenemedi.";
      setApplicationDocuments((items) =>
        items.map((document) =>
          document.id === documentId ? { ...document, file: undefined, status: "eksik", progress: 0 } : document,
        ),
      );
      showToast(message);
    }
  }

  async function handleSavedDocumentUpload(documentId: string, file: File) {
    const target = savedDocuments.find((document) => document.id === documentId);
    if (!target) return;

    setSavedDocuments((items) =>
      items.map((document) =>
        document.id === documentId ? { ...document, file, status: "inceleniyor", progress: 55 } : document,
      ),
    );

    try {
      const uploaded = await uploadDocument(target, file);
      setSavedDocuments((items) => replaceDocumentInPackage(items, uploaded));
      showToast(`${target.name} yüklendi.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Belge yuklenemedi.";
      setSavedDocuments((items) =>
        items.map((document) =>
          document.id === documentId ? { ...document, file: undefined, status: "eksik", progress: 0 } : document,
        ),
      );
      showToast(message);
    }
  }

  async function handleStartAnalysis() {
    if (!requiredDocumentsReady) {
      setApplicationDocuments((items) => items.map((document) => (document.file ? document : { ...document, status: "eksik" })));
      showToast("Analiz için kimlik, gelir belgesi ve banka dökümü yüklenmeli.");
      onNavigate("new-application");
      return;
    }
    if (!kvkkAccepted) {
      showToast("Analiz icin KVKK ve veri isleme onayini okumaniz ve kabul etmeniz gerekir.");
      onNavigate("new-application");
      return;
    }

    setAnalysisMessage("");
    setStages(baseStages);
    setAnalysisLoading(true);
    onNavigate("analysis-process");
    let analysisCompleted = false;

    try {
      const result = await runAnalysisWithVisibleStages(
        { ...form, kvkk_onayi: true, veri_isleme_onayi: true, gelir_turu: "Maas" },
        applicationDocuments,
        setStages,
      );
      setAnalysisResult(result);
      setSelectedApplicationId(result.applicationId);
      analysisCompleted = true;
      refreshCustomerData();
      setAnalysisMessage("AI analiz sureci tamamlandi. Sonuclar karar destek amaclidir; nihai karar banka onayiyla verilir.");
      showToast("AI analiz süreci tamamlandı.");
    } catch (error) {
      setAnalysisResult(null);
      const fallbackMessage = error instanceof Error ? error.message : "Analiz sonucu olusturulamadi.";
      setStages(markStageAsFailed(inferFailedStageId(fallbackMessage), fallbackMessage));
      setAnalysisMessage(fallbackMessage);
      showToast(fallbackMessage);
    }

    setAnalysisLoading(false);
    if (analysisCompleted) {
      onNavigate("analysis-results");
    }
  }

  async function handleAssistantSend(message: string) {
    if (!message.trim()) return;
    if (!paymentPlan) {
      showToast("AI finans asistanı için önce onaylı bir ödeme planı oluşmalı.");
      return;
    }

    const userMessage: AssistantMessage = { id: `u-${Date.now()}`, sender: "user", text: message };
    setAssistantMessages((items) => [...items, userMessage]);

    try {
      const answer = await sendAssistantMessage(paymentPlan.loan_id, message);
      const assistantMessage: AssistantMessage = { id: `a-${Date.now()}`, sender: "assistant", text: answer };
      setAssistantMessages((items) => [...items, assistantMessage]);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "AI finans asistanından cevap alınamadı.";
      const assistantMessage: AssistantMessage = { id: `a-${Date.now()}`, sender: "assistant", text: errorMessage };
      setAssistantMessages((items) => [...items, assistantMessage]);
      showToast(errorMessage);
    }
  }

  async function handleWalletTopUp(input: WalletTopUpInput): Promise<boolean> {
    setWalletActionLoading(true);
    try {
      const updatedWallet = await topUpWallet(input);
      setWallet(updatedWallet);
      showToast("Cüzdan bakiyesi yüklendi.");
      return true;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Cüzdan bakiyesi yüklenemedi.");
      return false;
    } finally {
      setWalletActionLoading(false);
    }
  }

  async function handlePayInstallment(installmentNo: number) {
    if (!paymentPlan) return;

    setWalletActionLoading(true);
    try {
      const result = await payInstallmentFromWallet(paymentPlan.loan_id, installmentNo);
      setPaymentPlan(result.paymentPlan);
      setWallet(result.wallet);
      showToast(`${installmentNo}. taksit ödendi.`);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Taksit ödenemedi.");
    } finally {
      setWalletActionLoading(false);
    }
  }

  async function handlePrincipalPayoff() {
    if (!paymentPlan) return;

    setWalletActionLoading(true);
    try {
      const result = await payRemainingPrincipalFromWallet(paymentPlan.loan_id);
      setPaymentPlan(result.paymentPlan);
      setWallet(result.wallet);
      showToast("Kalan ana para faizsiz kapatıldı.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Kalan ana para kapatılamadı.");
    } finally {
      setWalletActionLoading(false);
    }
  }

  async function handleProfileImageUpload(file: File) {
    setProfileImageLoading(true);
    try {
      const profileImage = await fileToProfileImage(file);
      const updatedUser = await updateCurrentProfile({ profile_image: profileImage });
      onUserUpdate(updatedUser);
      showToast("Profil fotoğrafı güncellendi.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Profil fotoğrafı güncellenemedi.");
    } finally {
      setProfileImageLoading(false);
    }
  }

  const applicationGroups = applicationGroupsWithApprovedCredit(customerApplications, paymentPlan, user);
  const latestPendingApplication = applicationGroups.pending[0] || null;
  const latestApprovedApplication = applicationGroups.approved[0] || null;
  const selectedApplication = customerApplications.find((application) => application.application_id === selectedApplicationId) || null;
  const focusedApplication = selectedApplication || latestPendingApplication || latestApprovedApplication || latestApplication;
  const focusedPaymentPlan = paymentPlan && paymentPlanBelongsToApplication(paymentPlan, focusedApplication) ? paymentPlan : null;
  const displayResult = analysisResult || analysisResultFromApplication(focusedApplication);

  if (activeView === "customer-home") {
    return <CustomerHome applications={customerApplications} documents={savedDocuments} result={displayResult} paymentPlan={paymentPlan} user={user} onNavigate={onNavigate} />;
  }
  if (activeView === "new-application") {
    return (
      <NewApplication
        documents={applicationDocuments}
        form={form}
        onFormChange={setForm}
        onStartAnalysis={handleStartAnalysis}
        onUpload={handleApplicationUpload}
        kvkkAccepted={kvkkAccepted}
        onKvkkChange={setKvkkAccepted}
        applicationReady={applicationReady}
        requiredDocumentsReady={requiredDocumentsReady}
        latestApplication={latestPendingApplication || latestApplication}
      />
    );
  }
  if (activeView === "documents") {
    return <DocumentsView documents={savedDocuments} latestApplication={latestPendingApplication || latestApplication} onUpload={handleSavedDocumentUpload} />;
  }
  if (activeView === "analysis-process") {
    return <AnalysisProcess applications={customerApplications} paymentPlan={paymentPlan} user={user} stages={stages} loading={analysisLoading} message={analysisMessage} onStartAnalysis={handleStartAnalysis} />;
  }
  if (activeView === "analysis-results") {
    return <AnalysisResults applications={customerApplications} paymentPlan={paymentPlan} user={user} result={displayResult} onNavigate={onNavigate} />;
  }
  if (activeView === "bank-approval") {
    return (
      <BankApproval
        applications={customerApplications}
        latestApplication={focusedApplication}
        onApplicationSelect={setSelectedApplicationId}
        onNavigate={onNavigate}
        paymentPlan={focusedPaymentPlan}
        result={displayResult}
        selectedApplicationId={focusedApplication?.application_id || selectedApplicationId}
      />
    );
  }
  if (activeView === "payment-plan") {
    return (
      <PaymentPlanView
        loading={walletActionLoading}
        onPayInstallment={handlePayInstallment}
        onPrincipalPayoff={handlePrincipalPayoff}
        onTopUp={handleWalletTopUp}
        paymentPlan={paymentPlan}
        wallet={wallet}
      />
    );
  }
  if (activeView === "assistant") {
    return <AssistantView messages={assistantMessages} onSend={handleAssistantSend} paymentPlan={paymentPlan} wallet={wallet} onNavigate={onNavigate} />;
  }
  if (activeView === "customer-settings") {
    return <SettingsView onAccountDeleted={onAccountDeleted} user={user} />;
  }
  return (
    <ProfileView
      applications={customerApplications}
      onProfileImageUpload={handleProfileImageUpload}
      paymentPlan={paymentPlan}
      profileImageLoading={profileImageLoading}
      user={user}
    />
  );
}

function CustomerHome({
  applications,
  result,
  documents,
  paymentPlan,
  user,
  onNavigate,
}: {
  applications: ApplicationRecord[];
  result: AnalysisResult | null;
  documents: UploadedDocument[];
  paymentPlan: PaymentPlan | null;
  user: User;
  onNavigate: (view: CustomerView) => void;
}) {
  const uploadedCount = documents.filter((document) => document.status === "yuklendi").length;
  const groups = applicationGroupsWithApprovedCredit(applications, paymentPlan, user);
  const focusedApplication = groups.pending[0] || groups.approved[0] || null;
  const hasApplication = groups.pending.length + groups.approved.length > 0;
  const heroTitle = hasApplication ? "Mevcut başvuru" : "Aktif başvuru yok";

  return (
    <div className="grid gap-5">
      <div className="grid gap-5 xl:grid-cols-[1fr_380px]">
        <Card className="min-h-[360px]">
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Müşteri Portalı</p>
          <h2 className="mt-3 font-display text-4xl font-bold">
            {heroTitle}
          </h2>
          <div className="mt-8 grid gap-4 md:grid-cols-4">
            <MetricCard label="Odak Skor" value={result ? result.eligibilityScore : "-"} hint={result ? focusedApplication?.application_id || "Son analiz" : "Analiz bekleniyor"} />
            <MetricCard label="Onaylanan" value={groups.approved.length} tone="green" />
            <MetricCard label="Onay Bekleyen" value={groups.pending.length} />
            <MetricCard label="Yüklenen Belge" value={`${uploadedCount}/${documents.length}`} tone="neutral" />
          </div>
          <ExtraDocumentNotice latestApplication={groups.pending[0] || null} onNavigate={onNavigate} />
          <div className="mt-8 flex flex-wrap gap-3">
            <button className="gold-gradient rounded-lg px-5 py-3 font-bold text-black" onClick={() => onNavigate("new-application")} type="button">
              Yeni başvuruya git
            </button>
            <button
              className="rounded-lg border border-white/10 px-5 py-3 text-muted disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!result && !applications.length}
              onClick={() => onNavigate("analysis-results")}
              type="button"
            >
              Analiz panellerini görüntüle
            </button>
          </div>
        </Card>
        <Card>
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Ödeme Özeti</p>
          <strong className="mt-4 block font-display text-3xl text-primary">{paymentPlan ? formatCurrency(paymentPlan.remaining_principal) : "-"}</strong>
          <span className="mt-1 block text-sm text-muted">{paymentPlan ? "Kalan ana para" : "Onaylı ödeme planı yok"}</span>
          <div className="mt-6 h-2 overflow-hidden rounded-full bg-white/10">
            <i className={`block h-full rounded-full bg-secondary ${paymentPlan ? "w-2/3" : "w-0"}`} />
          </div>
          <button
            className="gold-gradient mt-8 w-full rounded-lg px-5 py-3 font-bold text-black disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!paymentPlan}
            onClick={() => onNavigate("payment-plan")}
            type="button"
          >
            Ödeme planına git
          </button>
        </Card>
      </div>
      <ApplicationGroupGrid
        approved={groups.approved}
        pending={groups.pending}
        showReasons
      />
    </div>
  );
}

function NewApplication({
  documents,
  form,
  onFormChange,
  onStartAnalysis,
  onUpload,
  kvkkAccepted,
  onKvkkChange,
  applicationReady,
  requiredDocumentsReady,
  latestApplication,
}: {
  documents: UploadedDocument[];
  form: ApplicationForm;
  onFormChange: (form: ApplicationForm) => void;
  onStartAnalysis: () => void;
  onUpload: (documentId: string, file: File) => void;
  kvkkAccepted: boolean;
  onKvkkChange: (accepted: boolean) => void;
  applicationReady: boolean;
  requiredDocumentsReady: boolean;
  latestApplication: ApplicationRecord | null;
}) {
  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_0.86fr]">
      <Card>
        <div className="mb-5">
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Yeni Başvuru</p>
          <h2 className="mt-2 font-display text-3xl font-bold">Belge yükleme</h2>
          <p className="mt-2 text-sm text-muted">Kimlik, gelir belgesi ve banka dökümü zorunludur. Dosyalar backend analizine PDF olarak gönderilir.</p>
        </div>
        <ExtraDocumentNotice latestApplication={latestApplication} />
        <div className="grid gap-4">
          {documents.map((document) => (
            <UploadCard document={document} key={document.id} onUpload={onUpload} />
          ))}
        </div>
        <KvkkConsentBox accepted={kvkkAccepted} onAcceptedChange={onKvkkChange} />
      </Card>
      <Card>
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Başvuru Formu</p>
        <h2 className="mt-2 font-display text-3xl font-bold">Finansal bilgiler</h2>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          {formFieldOrder.map((key) => {
            const editable = editableFormFields.has(key);
            return (
              <label className="grid gap-2 text-sm text-muted" key={key}>
                {formLabel(key)}
                <input
                  className={`rounded-lg border px-4 py-3 text-white outline-none ${
                    editable
                      ? "border-white/10 bg-black/30 focus:border-primary/60"
                      : "border-white/10 bg-white/[0.04] text-muted"
                  }`}
                  readOnly={!editable}
                  value={form[key]}
                  onChange={(event) => onFormChange({ ...form, [key]: event.target.value })}
                />
              </label>
            );
          })}
        </div>
        <button
          className="gold-gradient mt-6 w-full rounded-lg px-5 py-3 font-bold text-black disabled:cursor-not-allowed disabled:opacity-60"
          disabled={!applicationReady}
          onClick={onStartAnalysis}
          type="button"
        >
          {applicationReady ? "AI analiz sürecini başlat" : requiredDocumentsReady ? "KVKK onayını tamamla" : "Belgeleri yükle ve analizi başlat"}
        </button>
      </Card>
    </div>
  );
}

function KvkkConsentBox({
  accepted,
  onAcceptedChange,
}: {
  accepted: boolean;
  onAcceptedChange: (accepted: boolean) => void;
}) {
  const [canAccept, setCanAccept] = useState(false);

  function handleScroll(event: UIEvent<HTMLDivElement>) {
    const target = event.currentTarget;
    const reachedBottom = target.scrollTop + target.clientHeight >= target.scrollHeight - 8;
    if (reachedBottom) {
      setCanAccept(true);
    }
  }

  return (
    <section className="mt-5 rounded-xl border border-white/10 bg-black/25 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <strong className="block">KVKK ve açık rıza metni</strong>
          <small className="text-muted">Metni sonuna kadar kaydırınca onay kutusu aktif olur.</small>
        </div>
        <StatusBadge tone={accepted ? "green" : "gold"}>{accepted ? "Onaylandı" : "Onay bekliyor"}</StatusBadge>
      </div>
      <div
        className="max-h-44 overflow-auto rounded-lg border border-white/10 bg-black/30 p-4 text-sm leading-relaxed text-muted"
        onScroll={handleScroll}
      >
        <p>
          CrediSense AI, kredi ön değerlendirme süreci için yüklediğiniz kimlik, gelir ve banka hesap dökümü belgelerini
          işler. Bu belgeler yalnızca başvuru analizi, belge tutarlılığı, finansal özellik çıkarımı ve banka uzmanı
          karar destek süreci için kullanılır.
        </p>
        <p className="mt-3">
          Sistem yapay zeka destekli skor ve açıklama üretir; nihai kredi kararı otomatik olarak verilmez. Nihai karar
          banka uzmanı ve banka onayı ile kesinleşir.
        </p>
        <p className="mt-3">
          Belgelerdeki kişi adı, oturumdaki kullanıcı adıyla karşılaştırılır. Farklı kişiye ait belge yüklenirse analiz
          süreci durdurulur ve başvuru kaydedilmez.
        </p>
        <p className="mt-3">
          Bu onayı vererek belgelerinizin CrediSense AI analiz katmanlarında işlenmesini, başvuru sonucunun banka uzmanı
          panelinde görüntülenmesini ve gerekli durumlarda ek belge talebi oluşturulmasını kabul edersiniz.
        </p>
      </div>
      <label className={`mt-4 flex items-start gap-3 text-sm ${canAccept ? "text-white" : "text-muted"}`}>
        <input
          checked={accepted}
          className="mt-1 h-4 w-4 accent-yellow-400 disabled:cursor-not-allowed"
          disabled={!canAccept}
          onChange={(event) => onAcceptedChange(event.target.checked)}
          type="checkbox"
        />
        <span>KVKK ve veri işleme metnini okudum, başvuru analizinde kullanılmasını onaylıyorum.</span>
      </label>
    </section>
  );
}

function DocumentsView({
  documents,
  latestApplication,
  onUpload,
}: {
  documents: UploadedDocument[];
  latestApplication: ApplicationRecord | null;
  onUpload: (documentId: string, file: File) => void;
}) {
  return (
    <Card>
      <div className="mb-5 flex items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Belgelerim</p>
          <h2 className="mt-2 font-display text-3xl font-bold">Yüklenen PDF belgeleri</h2>
        </div>
        <StatusBadge tone="gold">Servis bağlantısı hazır</StatusBadge>
      </div>
      <ExtraDocumentNotice latestApplication={latestApplication} />
      <div className="grid gap-4 md:grid-cols-2">
        {documents.map((document) => (
          <UploadCard document={document} key={document.id} onUpload={onUpload} />
        ))}
      </div>
    </Card>
  );
}

function AnalysisProcess({
  applications,
  paymentPlan,
  user,
  stages,
  loading,
  message,
  onStartAnalysis,
}: {
  applications: ApplicationRecord[];
  paymentPlan: PaymentPlan | null;
  user: User;
  stages: AnalysisStage[];
  loading: boolean;
  message: string;
  onStartAnalysis: () => void;
}) {
  const groups = applicationGroupsWithApprovedCredit(applications, paymentPlan, user);

  return (
    <div className="grid gap-5">
      <Card>
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">AI Analiz Süreci</p>
            <h2 className="mt-2 font-display text-3xl font-bold">Katmanlı analiz akışı</h2>
            <p className="mt-2 text-sm text-muted">Status değerleri backend analiz akışından alınır; hata olursa analiz kaydedilmez.</p>
          </div>
          <button className="gold-gradient rounded-lg px-5 py-3 font-bold text-black disabled:opacity-60" disabled={loading} onClick={onStartAnalysis} type="button">
            {loading ? "Analiz sürüyor" : "Analizi başlat"}
          </button>
        </div>
        {loading ? <LoadingState label="Belgeler katmanlı AI mimarisiyle işleniyor" /> : null}
        {message ? (
          <div className="mt-5 rounded-xl border border-primary/25 bg-primary/10 p-4 text-sm text-muted">
            {message}
          </div>
        ) : null}
        <div className="mt-5">
          <Stepper stages={stages} />
        </div>
      </Card>
      <ApplicationGroupGrid
        approved={groups.approved}
        pending={groups.pending}
        showReasons
      />
    </div>
  );
}

function AnalysisResults({
  applications,
  paymentPlan,
  user,
  result,
  onNavigate,
}: {
  applications: ApplicationRecord[];
  paymentPlan: PaymentPlan | null;
  user: User;
  result: AnalysisResult | null;
  onNavigate: (view: CustomerView) => void;
}) {
  const groups = applicationGroupsWithApprovedCredit(applications, paymentPlan, user);

  if (!result && !applications.length) {
    return (
      <Card>
        <EmptyState
          title="Henüz analiz sonucu yok"
          description="Sonuç ekranı, zorunlu PDF belgeleri yüklenip AI analiz süreci tamamlandıktan sonra gösterilir."
        />
        <button className="gold-gradient mx-auto mt-6 block rounded-lg px-5 py-3 font-bold text-black" onClick={() => onNavigate("new-application")} type="button">
          Başvuru ve belge yüklemeye git
        </button>
      </Card>
    );
  }

  return (
    <div className="grid gap-5">
      {result ? (
        <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
          <Card className="text-center">
            <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Müşteri Görünümü</p>
            <div className="mx-auto mt-8 grid h-44 w-44 place-items-center rounded-full border-[12px] border-primary/80 bg-primary/10 shadow-glow">
              <strong className="font-display text-5xl text-primary">{result.eligibilityScore}</strong>
            </div>
            <h2 className="mt-7 font-display text-3xl font-bold">Kredi uygunluk skoru</h2>
            <p className="mt-3 text-sm text-muted">Bu skor seçili analiz içindir. Diğer başvurular aşağıda ayrı tutulur.</p>
          </Card>
          <Card>
            <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Analiz Sonuçlarım</p>
            <h2 className="mt-2 font-display text-3xl font-bold">Açıklanabilir karar destek özeti</h2>
            <div className="mt-6 grid gap-4 md:grid-cols-3">
              <MetricCard label="Belge Güven Skoru" value={scorePercent(result.documentConfidenceScore)} tone="green" />
              <MetricCard label="Tutarlılık Skoru" value={scorePercent(result.consistencyScore)} />
              <MetricCard label="Anomali Skoru" value={scorePercent(result.anomalyScore)} tone="red" />
            </div>
            <p className="mt-6 rounded-xl border border-white/10 bg-black/25 p-4 text-muted">{result.summary}</p>
            <ul className="mt-5 grid gap-3">
              {result.reasons.map((reason) => (
                <li className="rounded-lg border border-white/10 bg-white/[0.03] p-3 text-sm text-muted" key={reason}>
                  {reason}
                </li>
              ))}
            </ul>
          </Card>
        </div>
      ) : null}
      <ApplicationGroupGrid
        approved={groups.approved}
        pending={groups.pending}
        showReasons
      />
    </div>
  );
}

function BankApproval({
  applications,
  latestApplication,
  selectedApplicationId,
  onApplicationSelect,
  result,
  paymentPlan,
  onNavigate,
}: {
  applications: ApplicationRecord[];
  latestApplication: ApplicationRecord | null;
  selectedApplicationId: string;
  onApplicationSelect: (applicationId: string) => void;
  result: AnalysisResult | null;
  paymentPlan: PaymentPlan | null;
  onNavigate: (view: CustomerView) => void;
}) {
  if (!latestApplication && !result) {
    return (
      <Card>
        <EmptyState
          title="Banka onay süreci başlamadı"
          description="Banka onayı ekranı, AI analiz sonucu oluşup başvuru uzman incelemesine düştükten sonra anlamlı hale gelir."
        />
        <button className="gold-gradient mx-auto mt-6 block rounded-lg px-5 py-3 font-bold text-black" onClick={() => onNavigate("new-application")} type="button">
          Analiz için başvuruya git
        </button>
      </Card>
    );
  }

  const statusCode = latestApplication?.status_code || "";
  const approved = statusCode === "APPROVED";
  const rejected = statusCode === "REJECTED";
  const statusText = approved ? "Onaylandi" : rejected ? "Reddedildi" : latestApplication?.status || "Beklemede";

  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Banka Onayı</p>
            <h2 className="mt-2 font-display text-3xl font-bold">Başvuru durumu</h2>
          </div>
          {applications.length > 1 ? (
            <label className="grid gap-2 text-sm text-muted">
              Başvuru seç
              <select
                className="min-w-64 rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-white outline-none focus:border-primary/60"
                onChange={(event) => onApplicationSelect(event.target.value)}
                value={selectedApplicationId}
              >
                {applications.map((application) => (
                  <option className="bg-[#101113]" key={application.application_id} value={application.application_id}>
                    {application.application_id} - {application.status || "Durum bekleniyor"}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <MetricCard label="AI Önerisi" value={latestApplication?.ai_recommendation ? "Karar destek hazır" : "Analiz bekleniyor"} />
          <MetricCard label="Banka Onayı" value={statusText} tone={approved ? "green" : rejected ? "red" : "neutral"} />
          <MetricCard label="Onaylanan Tutar" value={paymentPlan ? formatCurrency(paymentPlan.approved_amount) : approved ? "Ödeme planı hazırlanıyor" : "Banka onayı bekliyor"} />
          <MetricCard label="Vade" value={paymentPlan ? `${paymentPlan.maturity_months} Ay` : "-"} tone="neutral" />
        </div>
        <p className="mt-6 rounded-xl border border-primary/20 bg-primary/10 p-4 text-sm text-muted">
          {result?.aiRecommendation || latestApplication?.system_action || "Nihai karar banka onayıyla gösterilir."} Nihai karar banka onayıyla gösterilir.
        </p>
        {approved && paymentPlan ? (
          <button className="gold-gradient mt-6 rounded-lg px-5 py-3 font-bold text-black" onClick={() => onNavigate("payment-plan")} type="button">
            Ödeme planına git
          </button>
        ) : null}
      </Card>
      <Card>
        {paymentPlan ? (
          <ChartCard paymentPlan={paymentPlan} />
        ) : (
          <EmptyState
            title={approved ? "Ödeme planı hazırlanıyor" : "Ödeme planı yok"}
            description="Ödeme analitiği yalnızca banka onayı tamamlanıp gerçek ödeme planı oluştuğunda gösterilir."
          />
        )}
      </Card>
    </div>
  );
}

function PaymentPlanView({
  paymentPlan,
  wallet,
  loading,
  onTopUp,
  onPayInstallment,
  onPrincipalPayoff,
}: {
  paymentPlan: PaymentPlan | null;
  wallet: Wallet | null;
  loading: boolean;
  onTopUp: (input: WalletTopUpInput) => Promise<boolean>;
  onPayInstallment: (installmentNo: number) => Promise<void>;
  onPrincipalPayoff: () => Promise<void>;
}) {
  if (!paymentPlan) {
    return (
      <Card>
        <EmptyState
          title="Onaylı ödeme planı yok"
          description="Ödeme planı, banka uzmanı başvuruyu onaylayıp kredi planını oluşturduktan sonra gösterilir."
        />
      </Card>
    );
  }

  const walletBalance = wallet?.balance || 0;
  const monthlyInterestText = paymentPlan.monthly_interest_rate > 0 ? `%${(paymentPlan.monthly_interest_rate * 100).toFixed(2)}` : "-";
  const canPayPrincipal = paymentPlan.remaining_principal > 0 && walletBalance >= paymentPlan.remaining_principal;

  return (
    <Card>
      <div className="grid gap-5">
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Ödeme Planım</p>
        <h2 className="mt-2 font-display text-4xl font-bold text-primary">{formatCurrency(paymentPlan.approved_amount)}</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-4">
          <MetricCard label="Aylık Taksit" value={formatCurrency(paymentPlan.monthly_payment)} />
          <MetricCard label="Vade" value={`${paymentPlan.maturity_months} Ay`} tone="neutral" />
          <MetricCard label="Kalan Ana Para" value={formatCurrency(paymentPlan.remaining_principal)} />
          <MetricCard label="Aylık Faiz" value={monthlyInterestText} tone="gold" />
        </div>

        <div className="mt-3 grid gap-5 xl:grid-cols-[1fr_420px] xl:items-stretch">
          <div className="grid gap-5">
            <PrincipalPayoffPanel
              canPay={canPayPrincipal}
              loading={loading}
              onPayoff={onPrincipalPayoff}
              remainingPrincipal={paymentPlan.remaining_principal}
              walletBalance={walletBalance}
            />
            <ChartCard paymentPlan={paymentPlan} />
            <section className="flex max-h-[360px] min-h-[360px] flex-col rounded-xl border border-white/10 bg-black/25 p-4">
              <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Taksitler</p>
              <h3 className="mt-2 font-display text-2xl font-bold">Yaklaşan ödemeler</h3>
              <div className="mt-5 grid gap-3 overflow-y-auto pr-2">
                {paymentPlan.installments.map((installment) => {
                  const paid = installment.status === "Ödendi";
                  const canPay = !paid && walletBalance >= installment.amount;
                  return (
                    <div className="grid gap-3 rounded-lg border border-white/10 bg-black/25 p-4 md:grid-cols-[1fr_auto_auto_auto] md:items-center" key={installment.installment_no}>
                      <div>
                        <strong>Taksit {installment.installment_no}</strong>
                        <span className="mt-1 block text-xs text-muted">{formatDisplayDate(installment.due_date)}</span>
                      </div>
                      <span>{formatCurrency(installment.amount)}</span>
                      <StatusBadge tone={paid ? "green" : installment.status === "Gecikmiş" ? "red" : "gold"}>
                        {installment.status}
                      </StatusBadge>
                      <button
                        className="rounded-lg border border-primary/30 bg-primary/10 px-4 py-2 text-sm font-bold text-primary disabled:cursor-not-allowed disabled:opacity-50"
                        disabled={loading || paid || !canPay}
                        onClick={() => onPayInstallment(installment.installment_no)}
                        type="button"
                      >
                        {paid ? "Ödendi" : "Cüzdandan öde"}
                      </button>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>
          <WalletPanel loading={loading} onTopUp={onTopUp} wallet={wallet} />
        </div>
      </div>
    </Card>
  );
}

function PrincipalPayoffPanel({
  remainingPrincipal,
  walletBalance,
  canPay,
  loading,
  onPayoff,
}: {
  remainingPrincipal: number;
  walletBalance: number;
  canPay: boolean;
  loading: boolean;
  onPayoff: () => Promise<void>;
}) {
  const missingAmount = Math.max(0, remainingPrincipal - walletBalance);
  const closed = remainingPrincipal <= 0;

  return (
    <section className="rounded-xl border border-primary/20 bg-primary/10 p-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.14em] text-primary">Tek seferde kapama</p>
          <h3 className="mt-1 font-display text-xl font-bold">Kalan ana parayı faizsiz kapat</h3>
          <p className="mt-2 text-sm text-muted">
            {closed
              ? "Kredi ana para bakiyesi kapanmış görünüyor."
              : `Kalan ana para ${formatCurrency(remainingPrincipal)}. Bu işlem gelecek taksit faizlerini tahsil etmeden planı kapatır.`}
          </p>
          {!closed && !canPay ? (
            <p className="mt-2 text-sm text-danger">Cüzdanda kapama için {formatCurrency(missingAmount)} eksik var.</p>
          ) : null}
        </div>
        <button
          className="gold-gradient rounded-lg px-5 py-3 font-bold text-black disabled:cursor-not-allowed disabled:opacity-50"
          disabled={loading || closed || !canPay}
          onClick={onPayoff}
          type="button"
        >
          {closed ? "Kredi kapandı" : "Ana parayı kapat"}
        </button>
      </div>
    </section>
  );
}

function WalletPanel({
  wallet,
  loading,
  onTopUp,
}: {
  wallet: Wallet | null;
  loading: boolean;
  onTopUp: (input: WalletTopUpInput) => Promise<boolean>;
}) {
  const [form, setForm] = useState({
    amount: "",
    card_number: "",
    expiry_date: "",
    cvv: "",
    cardholder_name: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  function updateField(field: keyof typeof form, value: string) {
    const nextValue = field === "card_number"
      ? formatCardNumberInput(value)
      : field === "expiry_date"
        ? formatExpiryInput(value)
        : field === "cvv"
          ? value.replace(/\D/g, "").slice(0, 3)
          : value;
    setForm((current) => ({ ...current, [field]: nextValue }));
    setErrors((current) => ({ ...current, [field]: "" }));
  }

  async function submitTopUp() {
    const validationErrors = validateTopUpForm(form);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length) {
      return;
    }

    const success = await onTopUp({
      amount: parseMoneyValue(form.amount),
      card_number: form.card_number,
      expiry_date: form.expiry_date,
      cvv: form.cvv,
      cardholder_name: form.cardholder_name,
    });
    if (success) {
      setForm({ amount: "", card_number: "", expiry_date: "", cvv: "", cardholder_name: "" });
    }
  }

  return (
    <section className="rounded-xl border border-white/10 bg-black/25 p-4">
      <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Hesap Cüzdanı</p>
      <strong className="mt-3 block font-display text-3xl text-primary">{formatCurrency(wallet?.balance || 0)}</strong>
      <span className="text-sm text-muted">Kullanılabilir bakiye</span>

      <div className="mt-6 rounded-lg border border-white/10 bg-white/[0.03] p-4">
        <div className="flex items-center gap-2">
          {["VISA", "MC", "AMEX", "troy"].map((label) => (
            <span className="rounded border border-white/10 bg-white px-2 py-1 text-[10px] font-black text-black" key={label}>{label}</span>
          ))}
        </div>
        <div className="mt-4 grid gap-3">
          <CardInput
            error={errors.card_number}
            label="Kart numarası"
            onChange={(value) => updateField("card_number", value)}
            placeholder="0000 0000 0000 0000"
            value={form.card_number}
          />
          <div className="grid min-w-0 gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(96px,0.72fr)]">
            <CardInput
              error={errors.expiry_date}
              label="Son kullanma tarihi"
              onChange={(value) => updateField("expiry_date", value)}
              placeholder="AA/YY"
              value={form.expiry_date}
            />
            <CardInput
              error={errors.cvv}
              label="CVV"
              onChange={(value) => updateField("cvv", value)}
              placeholder="000"
              value={form.cvv}
            />
          </div>
          <CardInput
            error={errors.cardholder_name}
            label="Kart üzerindeki ad"
            onChange={(value) => updateField("cardholder_name", value)}
            placeholder="AD SOYAD"
            value={form.cardholder_name}
          />
          <CardInput
            error={errors.amount}
            label="Yüklenecek tutar"
            onChange={(value) => updateField("amount", value)}
            placeholder="10000"
            value={form.amount}
          />
          <button
            className="gold-gradient rounded-lg px-5 py-3 font-bold text-black disabled:cursor-not-allowed disabled:opacity-60"
            disabled={loading}
            onClick={submitTopUp}
            type="button"
          >
            {loading ? "İşleniyor" : "Bakiyeye yükle"}
          </button>
        </div>
      </div>

      <div className="mt-5 grid gap-3">
        <p className="font-mono text-xs uppercase tracking-[0.14em] text-muted">Son işlemler</p>
        {(wallet?.transactions || []).slice(0, 4).map((transaction) => (
          <div className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-black/20 p-3 text-sm" key={transaction.transaction_id}>
            <span className="text-muted">{transaction.description || "Cüzdan işlemi"}</span>
            <strong className={transaction.amount < 0 ? "text-danger" : "text-secondary"}>{formatCurrency(transaction.amount)}</strong>
          </div>
        ))}
        {!wallet?.transactions?.length ? <span className="text-sm text-muted">Henüz cüzdan işlemi yok.</span> : null}
      </div>
    </section>
  );
}

function CardInput({
  label,
  value,
  placeholder,
  error,
  onChange,
}: {
  label: string;
  value: string;
  placeholder: string;
  error?: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="grid min-w-0 gap-1 text-sm text-muted">
      <span className="truncate">{label}</span>
      <input
        className={`h-12 w-full min-w-0 rounded-lg border bg-black/30 px-4 py-3 text-white outline-none transition-colors focus:border-primary/60 ${error ? "border-danger/70" : "border-white/10"}`}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        value={value}
      />
      <span className="min-h-4 text-xs leading-4 text-danger">
        {error || null}
      </span>
    </label>
  );
}

function AssistantView({
  messages,
  onSend,
  paymentPlan,
  wallet,
  onNavigate,
}: {
  messages: AssistantMessage[];
  onSend: (message: string) => Promise<void>;
  paymentPlan: PaymentPlan | null;
  wallet: Wallet | null;
  onNavigate: (view: CustomerView) => void;
}) {
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);

  async function submitAssistantMessage(nextMessage: string) {
    const trimmedMessage = nextMessage.trim();
    if (!trimmedMessage || sending) {
      return;
    }

    setSending(true);
    try {
      await onSend(trimmedMessage);
    } finally {
      setSending(false);
    }
  }

  if (!paymentPlan) {
    return (
      <Card>
        <EmptyState
          title="AI finans asistanı için ödeme planı bekleniyor"
          description="Asistan, yalnızca bankanın onayladığı gerçek ödeme planı üzerinden cevap verir."
        />
        <button className="gold-gradient mx-auto mt-6 block rounded-lg px-5 py-3 font-bold text-black" onClick={() => onNavigate("new-application")} type="button">
          Başvuru oluştur
        </button>
      </Card>
    );
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
      <Card className="min-h-[640px]">
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">AI Finans Asistanı</p>
        <h2 className="mt-2 font-display text-3xl font-bold">Ödeme danışmanı</h2>
        <div className="mt-6 grid max-h-[440px] gap-4 overflow-auto pr-2">
          {messages.map((item) => (
            <article
              className={`max-w-[76%] rounded-xl border p-4 ${
                item.sender === "user"
                  ? "ml-auto border-primary/30 bg-primary/10"
                  : "border-white/10 bg-white/[0.04]"
              }`}
              key={item.id}
            >
              {item.text}
            </article>
          ))}
        </div>
        <form
          className="mt-6 grid grid-cols-[1fr_auto] gap-3"
          onSubmit={async (event) => {
            event.preventDefault();
            await submitAssistantMessage(message);
            setMessage("");
          }}
        >
          <input
            className="rounded-lg border border-white/10 bg-black/30 px-4 py-3 outline-none focus:border-primary/60"
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Asistana ödeme planınızla ilgili soru sorun"
            value={message}
          />
          <button className="gold-gradient rounded-lg px-5 py-3 font-bold text-black disabled:cursor-not-allowed disabled:opacity-60" disabled={sending} type="submit">
            {sending ? "Yazıyor" : "Gönder"}
          </button>
        </form>
      </Card>
      <Card>
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Kredi Özeti</p>
        <strong className="mt-4 block font-display text-3xl text-primary">{formatCurrency(paymentPlan.remaining_principal)}</strong>
        <span className="text-sm text-muted">Toplam kalan borç</span>
        <div className="mt-5 rounded-lg border border-white/10 bg-black/25 p-4">
          <span className="text-xs uppercase tracking-[0.12em] text-muted">Cüzdan bakiyesi</span>
          <strong className="mt-1 block text-xl text-secondary">{formatCurrency(wallet?.balance || 0)}</strong>
        </div>
        <div className="mt-8 grid gap-3">
          {assistantQuickQuestions(paymentPlan).map((question) => (
            <button
              className="rounded-lg border border-white/10 bg-white/[0.04] px-4 py-3 text-left text-muted hover:border-primary/40 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={sending}
              key={question}
              onClick={() => submitAssistantMessage(question)}
              type="button"
            >
              {question}
            </button>
          ))}
        </div>
      </Card>
    </div>
  );
}

function buildAssistantGreeting(user: User, paymentPlan?: PaymentPlan | null, wallet?: Wallet | null): AssistantMessage {
  const salutation = customerSalutation(user.fullName);
  const planSummary = paymentPlan
    ? `Kalan ana para ${formatCurrency(paymentPlan.remaining_principal)}, aylık taksit ${formatCurrency(paymentPlan.monthly_payment)} olarak görünüyor.`
    : "Ödeme planınız oluştuğunda kalan borç, taksit ve erken kapama bilgilerini buradan takip edebilirsiniz.";
  const walletText = wallet ? ` Cüzdan bakiyeniz ${formatCurrency(wallet.balance)}.` : "";
  const nextInstallment = paymentPlan ? nextPendingInstallment(paymentPlan) : null;
  const nextPaymentText = nextInstallment
    ? ` Sıradaki taksit ${formatDisplayDate(nextInstallment.due_date)} tarihinde ${formatCurrency(nextInstallment.amount)}.`
    : "";

  return {
    id: "assistant-greeting",
    sender: "assistant",
    text: `Merhaba ${salutation}. ${planSummary}${walletText}${nextPaymentText} Size nasıl yardımcı olabilirim?`,
  };
}

function assistantQuickQuestions(paymentPlan: PaymentPlan): string[] {
  const nextInstallment = nextPendingInstallment(paymentPlan);
  const remainingInstallmentCount = paymentPlan.installments.filter((installment) => installment.status !== "Ödendi").length;
  const nextQuestion = nextInstallment
    ? `Sıradaki taksitim ${formatDisplayDate(nextInstallment.due_date)} tarihinde mi?`
    : "Bekleyen taksitim var mı?";

  return [
    "Kalan borcum ne kadar?",
    "Aylık taksitim ne kadar?",
    nextQuestion,
    `Kaç taksitim kaldı? (${remainingInstallmentCount})`,
    "Cüzdan bakiyem sıradaki taksite yeterli mi?",
    "Toplam geri ödeme tutarım ne kadar?",
    "Erken kapama yapabilir miyim?",
    "Gecikmiş ödemem var mı?",
    "Taksit tarihimi değiştirebilir miyim?",
  ];
}

function customerSalutation(fullName: string): string {
  const cleanName = fullName.trim();
  if (!cleanName) {
    return "değerli müşterimiz";
  }

  const firstName = cleanName.split(/\s+/)[0];
  const lowerFirstName = firstName.toLocaleLowerCase("tr-TR");
  const femaleNames = new Set([
    "ayşe",
    "fatma",
    "zeynep",
    "elif",
    "seda",
    "merve",
    "esra",
    "eda",
    "gizem",
  ]);
  const title = femaleNames.has(lowerFirstName) ? "Hanım" : "Bey";
  return `${firstName} ${title}`;
}

function nextPendingInstallment(paymentPlan: PaymentPlan) {
  return paymentPlan.installments.find((installment) => installment.status !== "Ödendi") || null;
}

function formatDisplayDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value || "-";
  }
  return new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date);
}

function validateTopUpForm(form: {
  amount: string;
  card_number: string;
  expiry_date: string;
  cvv: string;
  cardholder_name: string;
}) {
  const errors: Record<string, string> = {};
  const amount = parseMoneyValue(form.amount);
  const cardDigits = form.card_number.replace(/\D/g, "");
  const cvvDigits = form.cvv.replace(/\D/g, "");
  const expiryStatus = validateExpiryDate(form.expiry_date);

  if (!Number.isFinite(amount) || amount <= 0) {
    errors.amount = "Yüklenecek tutar girilmeli.";
  }
  if (cardDigits.length !== 16) {
    errors.card_number = "Kart numarası 16 haneli olmalı.";
  }
  if (expiryStatus) {
    errors.expiry_date = expiryStatus;
  }
  if (cvvDigits.length !== 3) {
    errors.cvv = "CVV 3 haneli olmalı.";
  }
  if (!isRealisticCardholderName(form.cardholder_name)) {
    errors.cardholder_name = "Kart üzerindeki ad ve soyad gerçek isim formatında olmalı.";
  }

  return errors;
}

function validateExpiryDate(value: string) {
  const match = /^(0[1-9]|1[0-2])\/(\d{2})$/.exec(value);
  if (!match) {
    return "AA/YY formatında girilmeli.";
  }

  const expiryMonth = Number(match[1]);
  const expiryYear = 2000 + Number(match[2]);
  const now = new Date();
  const currentMonthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const expiryMonthStart = new Date(expiryYear, expiryMonth - 1, 1);
  if (expiryMonthStart < currentMonthStart) {
    return "Kart son kullanma tarihi geçmiş olamaz.";
  }

  return "";
}

function isRealisticCardholderName(value: string) {
  const nameParts = value
    .trim()
    .replace(/\s+/g, " ")
    .split(" ")
    .filter(Boolean);
  const letterPattern = /^[A-Za-zÇĞİÖŞÜçğıöşü'.-]+$/;
  const vowelPattern = /[AEIİOÖUÜaeıioöuü]/;

  return (
    nameParts.length >= 2
    && nameParts.every((part) => part.length >= 2 && letterPattern.test(part) && vowelPattern.test(part))
  );
}

function formatCardNumberInput(value: string) {
  return value
    .replace(/\D/g, "")
    .slice(0, 16)
    .replace(/(\d{4})(?=\d)/g, "$1 ")
    .trim();
}

function formatExpiryInput(value: string) {
  const digits = value.replace(/\D/g, "").slice(0, 4);
  if (digits.length <= 2) {
    return digits;
  }
  return `${digits.slice(0, 2)}/${digits.slice(2)}`;
}

function parseMoneyValue(value: unknown) {
  if (typeof value === "number") {
    return value;
  }
  if (typeof value !== "string") {
    return Number.NaN;
  }

  let text = value.replace(/[^0-9,.\-]/g, "");
  if (!text) {
    return Number.NaN;
  }

  if (text.includes(",") && text.includes(".")) {
    text = text.replace(/\./g, "").replace(",", ".");
  } else if (text.includes(",")) {
    text = text.replace(/\./g, "").replace(",", ".");
  } else if (text.includes(".")) {
    const parts = text.split(".");
    if (parts.length > 1 && parts.slice(1).every((part) => part.length === 3)) {
      text = parts.join("");
    }
  }

  return Number(text);
}

function ProfileView({
  applications,
  onProfileImageUpload,
  paymentPlan,
  profileImageLoading,
  user,
}: {
  applications: ApplicationRecord[];
  onProfileImageUpload: (file: File) => void;
  paymentPlan: PaymentPlan | null;
  profileImageLoading: boolean;
  user: User;
}) {
  const groups = applicationGroupsWithApprovedCredit(applications, paymentPlan, user);

  return (
    <div className="grid gap-5">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="flex flex-wrap items-center gap-5">
            <ProfileAvatar
              editable
              loading={profileImageLoading}
              onImageSelected={onProfileImageUpload}
              size="lg"
              user={user}
            />
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Profil</p>
              <h2 className="mt-2 font-display text-3xl font-bold">{user.fullName}</h2>
              <p className="mt-2 text-muted">{user.email}</p>
            </div>
          </div>
          <StatusBadge tone={user.emailVerified ? "green" : "gold"}>
            {user.emailVerified ? "E-posta doğrulandı" : "Doğrulama bekliyor"}
          </StatusBadge>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-4">
          <MetricCard label="Kullanıcı adı" value={user.username || "-"} tone="neutral" />
          <MetricCard label="Rol" value="Müşteri" tone="neutral" />
          <MetricCard label="Onaylanan" value={groups.approved.length} tone="green" />
          <MetricCard label="Onay Bekleyen" value={groups.pending.length} />
        </div>

        <div className="mt-6 grid gap-3 rounded-xl border border-white/10 bg-black/25 p-4 text-sm text-muted md:grid-cols-2">
          <DetailLine label="Aktif kredi" value={paymentPlan?.loan_id || String(user.profile?.active_loan_id || "-")} />
          <DetailLine label="Aktif başvuru" value={String(user.profile?.active_application_id || "-")} />
        </div>
      </Card>
      <ApplicationGroupGrid
        approved={groups.approved}
        pending={groups.pending}
        showReasons
      />
    </div>
  );
}

function ApplicationGroupGrid({
  approved,
  pending,
  showReasons = false,
}: {
  approved: ApplicationRecord[];
  pending: ApplicationRecord[];
  showReasons?: boolean;
}) {
  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <ApplicationListPanel
        applications={pending}
        description="Uzman kararı, ek belge veya banka onayı bekleyen başvurular."
        emptyDescription="Yeni analiz oluşturulduğunda banka onayı bekleyen kayıt burada görünür."
        emptyTitle="Onay bekleyen başvuru yok"
        showReasons={showReasons}
        title="Onay bekleyenler"
        tone="gold"
      />
      <ApplicationListPanel
        applications={approved}
        description="Banka onayı tamamlanan ve ödeme planına dönüşebilen başvurular."
        emptyDescription="Banka uzmanı başvuruyu onayladığında burada ayrı tutulur."
        emptyTitle="Onaylanan başvuru yok"
        showReasons={showReasons}
        title="Onaylananlar"
        tone="green"
      />
    </div>
  );
}

function ApplicationListPanel({
  applications,
  description,
  emptyDescription,
  emptyTitle,
  showReasons,
  title,
  tone,
}: {
  applications: ApplicationRecord[];
  description: string;
  emptyDescription: string;
  emptyTitle: string;
  showReasons: boolean;
  title: string;
  tone: "gold" | "green";
}) {
  return (
    <Card>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Başvuru Paneli</p>
          <h3 className="mt-2 font-display text-2xl font-bold">{title}</h3>
          <p className="mt-1 text-sm text-muted">{description}</p>
        </div>
        <StatusBadge tone={tone}>{`${applications.length} başvuru`}</StatusBadge>
      </div>

      {applications.length ? (
        <div className="grid gap-3">
          {applications.map((application) => (
            <CustomerApplicationCard application={application} key={application.application_id} showReasons={showReasons} />
          ))}
        </div>
      ) : (
        <EmptyState title={emptyTitle} description={emptyDescription} />
      )}
    </Card>
  );
}

function CustomerApplicationCard({
  application,
  showReasons,
}: {
  application: ApplicationRecord;
  showReasons: boolean;
}) {
  const reasons = applicationRiskReasons(application).slice(0, 4);

  return (
    <article className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
      <div className="grid gap-3 md:grid-cols-[1fr_auto] md:items-start">
        <div>
          <strong className="block">{application.application_id}</strong>
          <small className="text-muted">{application.created_at ? formatDisplayDate(application.created_at) : "Tarih bilgisi yok"}</small>
        </div>
        <StatusBadge tone={applicationRiskTone(application)}>{application.risk_level || "Risk bekleniyor"}</StatusBadge>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <CompactMetric label="Risk Skoru" value={applicationRiskScoreText(application)} tone={applicationRiskTone(application)} />
        <CompactMetric label="Durum" value={application.status || "Durum bekleniyor"} />
        <CompactMetric label="Talep" value={applicationAmountText(application)} />
      </div>

      {showReasons && reasons.length ? (
        <div className="mt-4 rounded-lg border border-white/10 bg-black/20 p-3">
          <strong className="text-sm">Skor gerekçeleri</strong>
          <ul className="mt-2 grid gap-2 text-sm text-muted">
            {reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </article>
  );
}

function CompactMetric({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "gold" | "green" | "red" | "neutral";
}) {
  const toneClass = tone === "red" ? "text-danger" : tone === "green" ? "text-secondary" : tone === "gold" ? "text-primary" : "text-white";
  return (
    <div className="min-w-0 rounded-lg border border-white/10 bg-black/25 p-3">
      <span className="block text-xs uppercase tracking-[0.12em] text-muted">{label}</span>
      <strong className={`mt-1 block truncate ${toneClass}`}>{value}</strong>
    </div>
  );
}

function DetailLine({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="block text-xs uppercase tracking-[0.12em] text-muted">{label}</span>
      <strong className="mt-1 block text-white">{value}</strong>
    </div>
  );
}

function SettingsView({
  onAccountDeleted,
  user,
}: {
  onAccountDeleted: () => Promise<void>;
  user: User;
}) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  async function handleConfirmDelete() {
    setDeleteLoading(true);
    try {
      await onAccountDeleted();
    } finally {
      setDeleteLoading(false);
      setConfirmOpen(false);
    }
  }

  return (
    <>
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Profil</p>
            <h2 className="mt-2 font-display text-3xl font-bold">{user.fullName}</h2>
            <p className="mt-2 text-muted">{user.email}</p>
          </div>
          <StatusBadge tone={user.emailVerified ? "green" : "gold"}>
            {user.emailVerified ? "E-posta doğrulandı" : "Doğrulama bekliyor"}
          </StatusBadge>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <MetricCard label="Kullanıcı adı" value={user.username || "-"} tone="neutral" />
          <MetricCard label="Rol" value="Müşteri" tone="neutral" />
          <MetricCard label="Aktif kredi" value={String(user.profile?.active_loan_id || "-")} tone="neutral" />
        </div>

        <div className="mt-8 rounded-xl border border-red-500/30 bg-red-500/10 p-5">
          <h3 className="font-display text-xl font-bold text-red-200">Hesap silme</h3>
          <p className="mt-2 text-sm text-muted">
            Hesap silme işlemi oturumu kapatır ve kullanıcı kaydını veritabanından kaldırır.
          </p>
          <button
            className="mt-5 rounded-lg border border-red-400/40 bg-red-500/20 px-5 py-3 font-bold text-red-100 transition hover:bg-red-500/30"
            onClick={() => setConfirmOpen(true)}
            type="button"
          >
            Hesabımı sil
          </button>
        </div>
      </Card>

      {confirmOpen ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 px-5 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-md rounded-2xl p-6 shadow-glow">
            <h3 className="font-display text-2xl font-bold">Hesap silinsin mi?</h3>
            <p className="mt-3 text-muted">Bu işleme devam etmek ister misiniz?</p>
            <div className="mt-6 grid grid-cols-2 gap-3">
              <button
                className="rounded-lg border border-white/10 px-5 py-3 font-bold text-muted transition hover:text-white"
                disabled={deleteLoading}
                onClick={() => setConfirmOpen(false)}
                type="button"
              >
                Vazgeç
              </button>
              <button
                className="rounded-lg border border-red-400/40 bg-red-500/25 px-5 py-3 font-bold text-red-100 transition hover:bg-red-500/35 disabled:opacity-70"
                disabled={deleteLoading}
                onClick={handleConfirmDelete}
                type="button"
              >
                {deleteLoading ? "Siliniyor" : "Evet, sil"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

function ExtraDocumentNotice({
  latestApplication,
  onNavigate,
}: {
  latestApplication: ApplicationRecord | null;
  onNavigate?: (view: CustomerView) => void;
}) {
  const requestedDocuments = latestApplication?.requested_documents || [];
  if (!requestedDocuments.length) {
    return null;
  }

  return (
    <div className="mt-6 rounded-xl border border-primary/30 bg-primary/10 p-4 text-sm">
      <strong>Ek belge talebi var</strong>
      <p className="mt-2 text-muted">
        Banka uzmanı bu başvuru için ek belge istedi. Aşağıdaki belgeler yükleme kartlarına eklendi.
      </p>
      <ul className="mt-3 grid gap-1 text-muted">
        {requestedDocuments.map((document) => <li key={document}>{document}</li>)}
      </ul>
      {onNavigate ? (
        <button className="gold-gradient mt-4 rounded-lg px-4 py-2 font-bold text-black" onClick={() => onNavigate("documents")} type="button">
          Belgeleri yükle
        </button>
      ) : null}
    </div>
  );
}

function formLabel(key: string): string {
  const labels: Record<string, string> = {
    full_name: "Ad Soyad",
    test_id: "Kimlik Numarası",
    birth_date: "Doğum Tarihi",
    employer: "İşveren",
    declared_income: "Beyan Edilen Gelir",
    requested_credit: "Talep Edilen Kredi",
    maturity_months: "Vade",
    existing_debt: "Mevcut Borç",
  };
  return labels[key] || key;
}

function createDocumentPackage(): UploadedDocument[] {
  return initialDocuments.map((document) => ({
    ...document,
    file: undefined,
    status: "bekliyor",
    progress: 0,
  }));
}

function replaceDocumentInPackage(documents: UploadedDocument[], updatedDocument: UploadedDocument): UploadedDocument[] {
  const exists = documents.some((document) => document.id === updatedDocument.id);
  if (!exists) {
    return [...documents, updatedDocument];
  }
  return documents.map((document) => (document.id === updatedDocument.id ? updatedDocument : document));
}

function buildDefaultForm(user: User): ApplicationForm {
  const profile = user.profile || {};
  return {
    full_name: user.fullName || defaultForm.full_name,
    test_id: String(profile.test_id || defaultForm.test_id),
    birth_date: String(profile.birth_date || defaultForm.birth_date),
    employer: String(profile.employer || defaultForm.employer),
    declared_income: String(profile.declared_income || defaultForm.declared_income),
    requested_credit: String(profile.requested_credit || defaultForm.requested_credit),
    maturity_months: String(profile.maturity_months || defaultForm.maturity_months),
    existing_debt: String(profile.existing_debt || defaultForm.existing_debt),
  };
}

function mergeExtractedFormFields(form: ApplicationForm, extractedFields: Partial<ApplicationForm>): ApplicationForm {
  const nextForm = { ...form };
  (Object.entries(extractedFields) as Array<[keyof ApplicationForm, string | undefined]>).forEach(([key, value]) => {
    if (editableFormFields.has(key)) {
      return;
    }
    const cleanValue = String(value || "").trim();
    if (cleanValue) {
      nextForm[key] = cleanValue;
    }
  });
  return nextForm;
}

function applicationGroupsWithApprovedCredit(
  applications: ApplicationRecord[],
  paymentPlan: PaymentPlan | null,
  user: User,
) {
  const groups = splitApplicationsByApproval(applications);
  const approvedCredit = approvedCreditApplicationRecord(paymentPlan, user);

  if (approvedCredit && !hasMatchingApprovedCredit(groups.approved, approvedCredit)) {
    groups.approved.unshift(approvedCredit);
  }

  return groups;
}

function approvedCreditApplicationRecord(paymentPlan: PaymentPlan | null, user: User): ApplicationRecord | null {
  if (!paymentPlan) {
    return null;
  }

  const profile = user.profile || {};
  const activeLoanId = paymentPlan.loan_id || String(profile.active_loan_id || "");
  const activeApplicationId = paymentPlan.application_id || String(profile.active_application_id || "");

  if (!activeLoanId && !activeApplicationId) {
    return null;
  }

  const requestedAmount = firstFiniteNumber(
    paymentPlan?.approved_amount,
    parseCurrencyValue(profile.requested_credit),
    parseCurrencyValue(profile.current_debt),
  );
  const remainingPrincipal = firstFiniteNumber(
    paymentPlan?.remaining_principal,
    parseCurrencyValue(profile.current_debt),
  );
  const termMonths = paymentPlan?.maturity_months ?? profile.maturity_months;

  return {
    application_id: activeApplicationId || activeLoanId,
    customer_name: user.fullName,
    status: "Kredi onaylandı, ödeme planı aktif",
    status_code: "APPROVED",
    risk_score: 29,
    risk_level: "Düşük",
    review_route: "completed",
    review_route_text: "Onaylanan kredi",
    system_action: "Banka onayı tamamlandı ve ödeme planı oluşturuldu.",
    ai_recommendation: "Onaylı kredi kaydı müşteri profilinden alındı.",
    credit_request: {
      requested_amount: Number.isFinite(requestedAmount) ? requestedAmount : undefined,
      term_months: termMonths ? String(termMonths) : undefined,
      current_total_debt: Number.isFinite(remainingPrincipal) ? remainingPrincipal : undefined,
    },
    reasons: [
      "Banka onayı tamamlandığı için bu kayıt onaylananlar panelinde tutulur.",
      `Aktif ödeme planı: ${activeLoanId}.`,
    ],
    raw: {
      source: "active_credit_profile",
      active_loan_id: activeLoanId,
      active_application_id: activeApplicationId,
      payment_plan_available: true,
    },
  };
}

function hasMatchingApprovedCredit(applications: ApplicationRecord[], approvedCredit: ApplicationRecord) {
  const raw = approvedCredit.raw as any;
  const activeLoanId = String(raw?.active_loan_id || "");
  const activeApplicationId = String(raw?.active_application_id || approvedCredit.application_id || "");

  return applications.some((application) => {
    const applicationRaw = application.raw as any;
    const applicationLoanId = String(applicationRaw?.loan_id || applicationRaw?.active_loan_id || "");
    return (
      application.application_id === activeApplicationId
      || (Boolean(activeLoanId) && applicationLoanId === activeLoanId)
    );
  });
}

function paymentPlanBelongsToApplication(paymentPlan: PaymentPlan, application: ApplicationRecord | null) {
  if (!application) {
    return false;
  }
  return Boolean(paymentPlan.application_id) && paymentPlan.application_id === application.application_id;
}

function splitApplicationsByApproval(applications: ApplicationRecord[]) {
  return applications.reduce(
    (groups, application) => {
      if (isApprovedApplication(application)) {
        groups.approved.push(application);
      } else {
        groups.pending.push(application);
      }
      return groups;
    },
    { approved: [] as ApplicationRecord[], pending: [] as ApplicationRecord[] },
  );
}

function isApprovedApplication(application: ApplicationRecord) {
  const raw = application.raw as any;
  const statusCode = String(application.status_code || raw?.current_status?.status_code || "").toUpperCase();
  const decisionType = String(raw?.bank_decision?.decision_type || raw?.expert_decision?.decision_type || "").toLowerCase();
  const statusText = normalizeTurkishText(application.status || raw?.current_status?.status_text || "");

  return statusCode === "APPROVED" || decisionType === "approve" || statusText.includes("onaylandi");
}

function applicationRiskReasons(application: ApplicationRecord) {
  const raw = application.raw as any;
  const values = [
    ...(application.reasons || []),
    ...(raw?.bank_view?.main_reasons || []),
    ...(raw?.risk?.reasons || []),
    ...(raw?.form_document_consistency?.flags || []),
    ...(raw?.consistency?.flags || []),
    application.system_action || "",
  ];
  const uniqueReasons = Array.from(new Set(values.map((item) => String(item).trim()).filter(Boolean)));

  if (uniqueReasons.length) {
    return uniqueReasons;
  }
  if (application.risk_level === "Yüksek" || application.risk_level === "Yuksek") {
    return ["Risk seviyesi yüksek olduğu için detaylı banka uzmanı incelemesi gerekir."];
  }
  if (application.risk_level === "Düşük" || application.risk_level === "Dusuk") {
    return ["Belge ve gelir göstergeleri düşük risk seviyesinde değerlendirildi."];
  }
  return ["Başvuru kaydı backend üzerinden yüklendi.", "Nihai karar banka uzmanı ve banka onayı ile takip edilir."];
}

function applicationRiskTone(application: ApplicationRecord): "gold" | "green" | "red" | "neutral" {
  if (application.risk_level === "Yüksek" || application.risk_level === "Yuksek") return "red";
  if (application.risk_level === "Düşük" || application.risk_level === "Dusuk") return "green";
  return "gold";
}

function applicationRiskScoreText(application: ApplicationRecord) {
  const value = Number(application.risk_score || 0);
  if (!Number.isFinite(value) || value <= 0) {
    return "-";
  }
  return value <= 1 ? scorePercent(value) : `%${Math.round(value)}`;
}

function applicationAmountText(application: ApplicationRecord) {
  const amount = parseCurrencyValue(application.credit_request?.requested_amount);
  if (Number.isFinite(amount) && amount > 0) {
    return formatCurrency(amount);
  }
  const rawAmount = application.credit_request?.requested_amount;
  return rawAmount ? String(rawAmount) : "-";
}

function analysisResultFromApplication(application: ApplicationRecord | null): AnalysisResult | null {
  if (!application) {
    return null;
  }

  const riskScore = Number(application.risk_score || 0);
  const eligibilityScore = riskScore ? Math.max(0, Math.min(100, 100 - riskScore)) : 0;
  const reasons = applicationRiskReasons(application);

  return {
    applicationId: application.application_id,
    eligibilityScore,
    riskScore,
    riskLevel: application.risk_level || "Bekleniyor",
    documentConfidenceScore: application.document_confidence_score ?? 0,
    consistencyScore: application.consistency_score ?? 0,
    anomalyScore: application.anomaly_score ?? 0,
    aiRecommendation: application.ai_recommendation || "AI sonucu karar destek amaçlıdır.",
    summary: application.system_action || application.status || "Başvuru durumu backend kaydından alındı.",
    reasons,
    raw: application.raw,
  };
}

function parseCurrencyValue(value: unknown) {
  if (typeof value === "number") {
    return value;
  }
  if (typeof value !== "string") {
    return Number.NaN;
  }

  let text = value.replace(/[^0-9,.\-]/g, "");
  if (!text) {
    return Number.NaN;
  }
  if (text.includes(",") && text.includes(".")) {
    text = text.replace(/\./g, "").replace(",", ".");
  } else if (text.includes(",")) {
    text = text.replace(/\./g, "").replace(",", ".");
  } else if (text.includes(".")) {
    const parts = text.split(".");
    if (parts.length > 1 && parts.slice(1).every((part) => part.length === 3)) {
      text = parts.join("");
    }
  }
  return Number(text);
}

function firstFiniteNumber(...values: Array<number | undefined>) {
  return values.find((value) => Number.isFinite(value)) ?? Number.NaN;
}

function normalizeTurkishText(value: string) {
  return value
    .replace(/[Çç]/g, "c")
    .replace(/[Ğğ]/g, "g")
    .replace(/[İIı]/g, "i")
    .replace(/[Öö]/g, "o")
    .replace(/[Şş]/g, "s")
    .replace(/[Üü]/g, "u")
    .toLowerCase();
}

async function runAnalysisWithVisibleStages(
  form: ApplicationForm & Record<string, unknown>,
  documents: UploadedDocument[],
  setStages: Dispatch<SetStateAction<AnalysisStage[]>>,
) {
  type StepResult =
    | { type: "done"; result: AnalysisResult }
    | { type: "error"; error: unknown }
    | { type: "tick" };

  const analysisPromise = startBackendAnalysis(form, documents);
  const watchedAnalysis = analysisPromise
    .then((result) => ({ type: "done" as const, result }))
    .catch((error) => ({ type: "error" as const, error }));
  let completedResult: AnalysisResult | null = null;

  for (let index = 0; index < baseStages.length; index += 1) {
    setStages((items) =>
      items.map((stage, stageIndex) => ({
        ...stage,
        errorMessage: "",
        status: stageIndex < index ? "tamamlandi" : stageIndex === index ? "calisiyor" : "bekliyor",
      })),
    );

    const stepResult: StepResult = completedResult
      ? await wait(700).then(() => ({ type: "tick" as const }))
      : await Promise.race([
          watchedAnalysis,
          wait(700).then(() => ({ type: "tick" as const })),
        ]);

    if (stepResult.type === "done") {
      completedResult = stepResult.result;
    }
    if (stepResult.type === "error") {
      throw stepResult.error;
    }
  }

  const result = completedResult || await analysisPromise;
  setStages(baseStages.map((stage) => ({ ...stage, status: "tamamlandi", errorMessage: "" })));
  return result;
}

function markStageAsFailed(failedStageId: string, message: string): AnalysisStage[] {
  let failedStageSeen = false;
  return baseStages.map((stage) => {
    if (stage.id === failedStageId) {
      failedStageSeen = true;
      return { ...stage, status: "hata", errorMessage: message };
    }
    return {
      ...stage,
      status: failedStageSeen ? "bekliyor" : "tamamlandi",
      errorMessage: "",
    };
  });
}

function inferFailedStageId(message: string): string {
  const normalized = message.toLowerCase();
  if (normalized.includes("pdf") || normalized.includes("dosya")) return "pdf";
  if (normalized.includes("belge paketi") || normalized.includes("yanlis belge") || normalized.includes("yanlış belge")) return "understanding";
  if (normalized.includes("belge tipi") || normalized.includes("okunamad")) return "understanding";
  if (normalized.includes("eslesm") || normalized.includes("eşleşm") || normalized.includes("uyumsuz")) return "consistency";
  if (normalized.includes("gelir") || normalized.includes("banka")) return "features";
  return "risk";
}

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function mergeRequestedDocuments(documents: UploadedDocument[], requestedDocuments: string[]) {
  const merged = [...documents];

  requestedDocuments.forEach((documentName) => {
    const id = `extra-${slugify(documentName)}`;
    const exists = merged.some((document) => document.id === id || document.name === documentName);
    if (!exists) {
      merged.push({
        id,
        name: documentName,
        type: "Ek belge",
        status: "bekliyor",
        progress: 0,
      });
    }
  });

  return merged;
}

function slugify(value: string) {
  return value
    .toLowerCase()
    .replace(/[ç]/g, "c")
    .replace(/[ğ]/g, "g")
    .replace(/[ı]/g, "i")
    .replace(/[ö]/g, "o")
    .replace(/[ş]/g, "s")
    .replace(/[ü]/g, "u")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
