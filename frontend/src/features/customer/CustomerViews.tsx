"use client";

import { useEffect, useRef, useState, type Dispatch, type SetStateAction, type UIEvent } from "react";
import { Card } from "@/components/ui/Card";
import { ChartCard } from "@/components/ui/ChartCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Stepper } from "@/components/ui/Stepper";
import { UploadCard } from "@/components/ui/UploadCard";
import { initialDocuments } from "@/lib/demoData";
import { formatCurrency, scorePercent } from "@/lib/format";
import { startAnalysis as startBackendAnalysis } from "@/services/analysisService";
import { getCustomerApplications } from "@/services/applicationService";
import { getDocuments, uploadDocument } from "@/services/documentService";
import { getApprovedLoanPlan } from "@/services/paymentService";
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
} from "@/types";

type CustomerViewsProps = {
  activeView: CustomerView;
  onAccountDeleted: () => Promise<void>;
  onNavigate: (view: CustomerView) => void;
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

const baseStages: AnalysisStage[] = [
  { id: "pdf", title: "PDF Okuma", description: "Yüklenen belgelerden metin çıkarılır.", status: "bekliyor" },
  { id: "understanding", title: "Belge Anlama", description: "Kimlik, gelir ve banka dökümü alanları ayrıştırılır.", status: "bekliyor" },
  { id: "consistency", title: "Tutarlılık", description: "Belgeler ve form verileri karşılaştırılır.", status: "bekliyor" },
  { id: "features", title: "Finansal Özellikler", description: "Gelir, harcama ve nakit akışı özellikleri hesaplanır.", status: "bekliyor" },
  { id: "risk", title: "Risk Tahmini", description: "Karar destek skoru üretilir.", status: "bekliyor" },
];

export function CustomerViews({ activeView, onAccountDeleted, onNavigate, showToast, user }: CustomerViewsProps) {
  const [applicationDocuments, setApplicationDocuments] = useState<UploadedDocument[]>(() => createDocumentPackage());
  const [savedDocuments, setSavedDocuments] = useState<UploadedDocument[]>(() => createDocumentPackage());
  const [form, setForm] = useState<ApplicationForm>(() => buildDefaultForm(user));
  const [stages, setStages] = useState<AnalysisStage[]>(baseStages);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [customerApplications, setCustomerApplications] = useState<ApplicationRecord[]>([]);
  const [latestApplication, setLatestApplication] = useState<ApplicationRecord | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisMessage, setAnalysisMessage] = useState("");
  const [kvkkAccepted, setKvkkAccepted] = useState(false);
  const [paymentPlan, setPaymentPlan] = useState<PaymentPlan | null>(null);
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
      const nextGreeting = buildAssistantGreeting(user, paymentPlan);
      if (!items.length) {
        return [nextGreeting];
      }
      if (items[0].id !== nextGreeting.id) {
        return items;
      }
      return [nextGreeting, ...items.slice(1)];
    });
  }, [user.fullName, paymentPlan?.loan_id, paymentPlan?.monthly_payment, paymentPlan?.remaining_principal]);

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
    const [documentResult, applicationResult, paymentResult] = await Promise.allSettled([
      getDocuments(createDocumentPackage()),
      getCustomerApplications(),
      getApprovedLoanPlan(),
    ]);

    const nextApplications = applicationResult.status === "fulfilled" ? applicationResult.value : [];
    const latest = nextApplications[0] || null;
    const nextDocuments = documentResult.status === "fulfilled" ? documentResult.value : createDocumentPackage();

    setCustomerApplications(nextApplications);
    setLatestApplication(latest);
    setSavedDocuments(mergeRequestedDocuments(nextDocuments, latest?.requested_documents || []));
    setPaymentPlan(paymentResult.status === "fulfilled" ? paymentResult.value : null);
  }

  async function handleApplicationUpload(documentId: string, file: File) {
    const target = applicationDocuments.find((document) => document.id === documentId);
    if (!target) return;

    setApplicationDocuments((items) =>
      items.map((document) =>
        document.id === documentId ? { ...document, file, status: "inceleniyor", progress: 55 } : document,
      ),
    );

    const uploaded = await uploadDocument(target, file);
    setApplicationDocuments((items) => items.map((document) => (document.id === documentId ? uploaded : document)));
    setSavedDocuments((items) => replaceDocumentInPackage(items, uploaded));
    showToast(`${target.name} yüklendi.`);
  }

  async function handleSavedDocumentUpload(documentId: string, file: File) {
    const target = savedDocuments.find((document) => document.id === documentId);
    if (!target) return;

    setSavedDocuments((items) =>
      items.map((document) =>
        document.id === documentId ? { ...document, file, status: "inceleniyor", progress: 55 } : document,
      ),
    );

    const uploaded = await uploadDocument(target, file);
    setSavedDocuments((items) => replaceDocumentInPackage(items, uploaded));
    showToast(`${target.name} yüklendi.`);
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

  const displayResult = analysisResult || analysisResultFromApplication(latestApplication);

  if (activeView === "customer-home") {
    return <CustomerHome result={displayResult} documents={savedDocuments} latestApplication={latestApplication} paymentPlan={paymentPlan} onNavigate={onNavigate} />;
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
        latestApplication={latestApplication}
      />
    );
  }
  if (activeView === "documents") {
    return <DocumentsView documents={savedDocuments} latestApplication={latestApplication} onUpload={handleSavedDocumentUpload} />;
  }
  if (activeView === "analysis-process") {
    return <AnalysisProcess stages={stages} loading={analysisLoading} message={analysisMessage} onStartAnalysis={handleStartAnalysis} />;
  }
  if (activeView === "analysis-results") {
    return <AnalysisResults result={displayResult} onNavigate={onNavigate} />;
  }
  if (activeView === "bank-approval") {
    return <BankApproval latestApplication={latestApplication} paymentPlan={paymentPlan} result={displayResult} onNavigate={onNavigate} />;
  }
  if (activeView === "payment-plan") {
    return <PaymentPlanView paymentPlan={paymentPlan} />;
  }
  if (activeView === "assistant") {
    return <AssistantView messages={assistantMessages} onSend={handleAssistantSend} paymentPlan={paymentPlan} onNavigate={onNavigate} />;
  }
  if (activeView === "customer-settings") {
    return <SettingsView onAccountDeleted={onAccountDeleted} user={user} />;
  }
  return <ProfileView applications={customerApplications} user={user} />;
}

function CustomerHome({
  result,
  documents,
  latestApplication,
  paymentPlan,
  onNavigate,
}: {
  result: AnalysisResult | null;
  documents: UploadedDocument[];
  latestApplication: ApplicationRecord | null;
  paymentPlan: PaymentPlan | null;
  onNavigate: (view: CustomerView) => void;
}) {
  const uploadedCount = documents.filter((document) => document.status === "yuklendi").length;
  const hasApplication = Boolean(latestApplication);
  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_380px]">
      <Card className="min-h-[360px]">
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Müşteri Portalı</p>
        <h2 className="mt-3 font-display text-4xl font-bold">
          {hasApplication ? "Başvuru durumunuz kontrol altında" : "Henüz aktif başvurunuz yok"}
        </h2>
        <p className="mt-4 max-w-2xl text-muted">
          {hasApplication
            ? "AI analizleri karar destek amacıyla çalışır. Nihai kredi kararı banka uzmanı ve banka onayı ile kesinleşir."
            : "Kredi uygunluk skoru, banka onayı ve ödeme planı ancak PDF belgeleri yüklenip başvuru oluştuktan sonra gösterilir."}
        </p>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          <MetricCard label="Kredi Uygunluk Skoru" value={result ? result.eligibilityScore : "-"} hint={result ? "Müşteri görünümü" : "Analiz bekleniyor"} />
          <MetricCard label="Başvuru Durumu" value={latestApplication?.status || "Başvuru yok"} tone={latestApplication ? "green" : "neutral"} />
          <MetricCard label="Yüklenen Belge" value={`${uploadedCount}/${documents.length}`} tone="neutral" />
        </div>
        <ExtraDocumentNotice latestApplication={latestApplication} onNavigate={onNavigate} />
        <div className="mt-8 flex flex-wrap gap-3">
          <button className="gold-gradient rounded-lg px-5 py-3 font-bold text-black" onClick={() => onNavigate("new-application")} type="button">
            Yeni başvuruya git
          </button>
          <button
            className="rounded-lg border border-white/10 px-5 py-3 text-muted disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!result}
            onClick={() => onNavigate("analysis-results")}
            type="button"
          >
            Analiz sonucunu görüntüle
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
          {Object.entries(form).map(([key, value]) => (
            <label className="grid gap-2 text-sm text-muted" key={key}>
              {formLabel(key)}
              <input
                className="rounded-lg border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-primary/60"
                value={value}
                onChange={(event) => onFormChange({ ...form, [key]: event.target.value })}
              />
            </label>
          ))}
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
  stages,
  loading,
  message,
  onStartAnalysis,
}: {
  stages: AnalysisStage[];
  loading: boolean;
  message: string;
  onStartAnalysis: () => void;
}) {
  return (
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
  );
}

function AnalysisResults({ result, onNavigate }: { result: AnalysisResult | null; onNavigate: (view: CustomerView) => void }) {
  if (!result) {
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
    <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
      <Card className="text-center">
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Müşteri Görünümü</p>
        <div className="mx-auto mt-8 grid h-44 w-44 place-items-center rounded-full border-[12px] border-primary/80 bg-primary/10 shadow-glow">
          <strong className="font-display text-5xl text-primary">{result.eligibilityScore}</strong>
        </div>
        <h2 className="mt-7 font-display text-3xl font-bold">Kredi uygunluk skoru</h2>
        <p className="mt-3 text-sm text-muted">Bu skor nihai karar değildir. Banka onayı ayrı süreçtir.</p>
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
  );
}

function BankApproval({
  latestApplication,
  result,
  paymentPlan,
  onNavigate,
}: {
  latestApplication: ApplicationRecord | null;
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
  const approved = Boolean(paymentPlan) || statusCode === "APPROVED";
  const rejected = statusCode === "REJECTED";
  const statusText = approved ? "Onaylandi" : rejected ? "Reddedildi" : latestApplication?.status || "Beklemede";

  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <Card>
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Banka Onayı</p>
        <h2 className="mt-2 font-display text-3xl font-bold">Başvuru durumu</h2>
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
        <ChartCard />
      </Card>
    </div>
  );
}

function PaymentPlanView({ paymentPlan }: { paymentPlan: PaymentPlan | null }) {
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

  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_420px]">
      <Card>
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Ödeme Planım</p>
        <h2 className="mt-2 font-display text-4xl font-bold text-primary">{formatCurrency(paymentPlan.approved_amount)}</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <MetricCard label="Aylık Taksit" value={formatCurrency(paymentPlan.monthly_payment)} />
          <MetricCard label="Vade" value={`${paymentPlan.maturity_months} Ay`} tone="neutral" />
          <MetricCard label="Kalan Ana Para" value={formatCurrency(paymentPlan.remaining_principal)} />
        </div>
        <div className="mt-8">
          <ChartCard />
        </div>
      </Card>
      <Card>
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Taksitler</p>
        <h2 className="mt-2 font-display text-2xl font-bold">Yaklaşan ödemeler</h2>
        <div className="mt-5 grid gap-3">
          {paymentPlan.installments.map((installment) => (
            <div className="grid grid-cols-[1fr_auto_auto] items-center gap-3 rounded-lg border border-white/10 bg-black/25 p-4" key={installment.installment_no}>
              <strong>Taksit {installment.installment_no}</strong>
              <span>{formatCurrency(installment.amount)}</span>
              <StatusBadge tone={installment.status === "Ödendi" ? "green" : installment.status === "Gecikmiş" ? "red" : "gold"}>
                {installment.status}
              </StatusBadge>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function AssistantView({
  messages,
  onSend,
  paymentPlan,
  onNavigate,
}: {
  messages: AssistantMessage[];
  onSend: (message: string) => Promise<void>;
  paymentPlan: PaymentPlan | null;
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

function buildAssistantGreeting(user: User, paymentPlan?: PaymentPlan | null): AssistantMessage {
  const salutation = customerSalutation(user.fullName);
  const planSummary = paymentPlan
    ? `Kalan ana para ${formatCurrency(paymentPlan.remaining_principal)}, aylık taksit ${formatCurrency(paymentPlan.monthly_payment)} olarak görünüyor.`
    : "Ödeme planınız oluştuğunda kalan borç, taksit ve erken kapama bilgilerini buradan takip edebilirsiniz.";
  const nextInstallment = paymentPlan ? nextPendingInstallment(paymentPlan) : null;
  const nextPaymentText = nextInstallment
    ? ` Sıradaki taksit ${formatDisplayDate(nextInstallment.due_date)} tarihinde ${formatCurrency(nextInstallment.amount)}.`
    : "";

  return {
    id: "assistant-greeting",
    sender: "assistant",
    text: `Merhaba ${salutation}. ${planSummary}${nextPaymentText} Size nasıl yardımcı olabilirim?`,
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

function ProfileView({ applications, user }: { applications: ApplicationRecord[]; user: User }) {
  return (
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

      <div className="mt-8 rounded-xl border border-white/10 bg-black/20 p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-display text-xl font-bold">Gecmis basvurular</h3>
            <p className="mt-1 text-sm text-muted">Bu hesapla olusturulan eski kredi basvuru paketleri.</p>
          </div>
          <StatusBadge tone="gold">{`${applications.length} basvuru`}</StatusBadge>
        </div>

        {applications.length ? (
          <div className="grid gap-3">
            {applications.map((application) => (
              <article className="grid gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-4 md:grid-cols-[1fr_auto_auto]" key={application.application_id}>
                <div>
                  <strong className="block">{application.application_id}</strong>
                  <small className="text-muted">{application.created_at || "Tarih bilgisi yok"}</small>
                </div>
                <StatusBadge tone={application.risk_level === "Yuksek" || application.risk_level === "Yüksek" ? "red" : application.risk_level === "Dusuk" || application.risk_level === "Düşük" ? "green" : "gold"}>
                  {application.risk_level || "Risk bekleniyor"}
                </StatusBadge>
                <span className="text-sm text-muted">{application.status}</span>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState
            title="Gecmis basvuru yok"
            description="Yeni basvuru tamamlandiginda bu bolumde ayri bir kayit olarak gorunur."
          />
        )}
      </div>
    </Card>
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
    test_id: "Test Kimlik No",
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

function analysisResultFromApplication(application: ApplicationRecord | null): AnalysisResult | null {
  if (!application) {
    return null;
  }

  const riskScore = Number(application.risk_score || 0);
  const eligibilityScore = riskScore ? Math.max(0, Math.min(100, 100 - riskScore)) : 0;
  const reasons = application.reasons?.length ? application.reasons : [
    application.system_action || "Başvuru kaydı backend üzerinden yüklendi.",
    "Nihai karar banka uzmanı ve banka onayı ile takip edilir.",
  ];

  return {
    applicationId: application.application_id,
    eligibilityScore,
    riskScore,
    riskLevel: application.risk_level || "Bekleniyor",
    documentConfidenceScore: application.document_confidence_score || 0,
    consistencyScore: application.consistency_score || 0,
    anomalyScore: application.anomaly_score || 0,
    aiRecommendation: application.ai_recommendation || "AI sonucu karar destek amaçlıdır.",
    summary: application.system_action || application.status || "Başvuru durumu backend kaydından alındı.",
    reasons,
    raw: application.raw,
  };
}

async function runAnalysisWithVisibleStages(
  form: ApplicationForm & Record<string, unknown>,
  documents: UploadedDocument[],
  setStages: Dispatch<SetStateAction<AnalysisStage[]>>,
) {
  const analysisPromise = startBackendAnalysis(form, documents);
  const watchedAnalysis = analysisPromise
    .then((result) => ({ type: "done" as const, result }))
    .catch((error) => ({ type: "error" as const, error }));

  for (let index = 0; index < baseStages.length; index += 1) {
    setStages((items) =>
      items.map((stage, stageIndex) => ({
        ...stage,
        errorMessage: "",
        status: stageIndex < index ? "tamamlandi" : stageIndex === index ? "calisiyor" : "bekliyor",
      })),
    );

    const stepResult = await Promise.race([
      watchedAnalysis,
      wait(700).then(() => ({ type: "tick" as const })),
    ]);

    if (stepResult.type === "done") {
      setStages(baseStages.map((stage) => ({ ...stage, status: "tamamlandi", errorMessage: "" })));
      return stepResult.result;
    }
    if (stepResult.type === "error") {
      throw stepResult.error;
    }
  }

  const result = await analysisPromise;
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
