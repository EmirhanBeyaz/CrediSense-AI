"use client";

import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/Card";
import { ChartCard } from "@/components/ui/ChartCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Stepper } from "@/components/ui/Stepper";
import { UploadCard } from "@/components/ui/UploadCard";
import { demoAnalysisResult, demoPaymentPlan, initialDocuments } from "@/lib/demoData";
import { formatCurrency, scorePercent } from "@/lib/format";
import { startAnalysis as startBackendAnalysis } from "@/services/analysisService";
import { getDocuments, uploadDocument } from "@/services/documentService";
import { getApprovedLoanPlan } from "@/services/paymentService";
import { sendAssistantMessage } from "@/services/assistantService";
import type {
  AnalysisResult,
  AnalysisStage,
  ApplicationForm,
  AssistantMessage,
  CustomerView,
  PaymentPlan,
  UploadedDocument,
  User,
} from "@/types";

type CustomerViewsProps = {
  activeView: CustomerView;
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

export function CustomerViews({ activeView, onNavigate, showToast, user }: CustomerViewsProps) {
  const [documents, setDocuments] = useState<UploadedDocument[]>(initialDocuments);
  const [form, setForm] = useState<ApplicationForm>(() => buildDefaultForm(user));
  const [stages, setStages] = useState<AnalysisStage[]>(baseStages);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [paymentPlan, setPaymentPlan] = useState<PaymentPlan>(demoPaymentPlan);
  const [assistantMessages, setAssistantMessages] = useState<AssistantMessage[]>([
    {
      id: "m1",
      sender: "assistant",
      text: "Merhaba Deniz Bey. Ödeme planınızı ve yaklaşan taksitlerinizi analiz ettim. Size nasıl yardımcı olabilirim?",
    },
  ]);

  const requiredDocumentsReady = documents.filter((document) => document.id !== "kvkk").every((document) => document.file);

  useEffect(() => {
    getApprovedLoanPlan().then(setPaymentPlan).catch(() => setPaymentPlan(demoPaymentPlan));
    getDocuments(initialDocuments).then(setDocuments).catch(() => setDocuments(initialDocuments));
  }, []);

  async function handleUpload(documentId: string, file: File) {
    const target = documents.find((document) => document.id === documentId);
    if (!target) return;

    setDocuments((items) =>
      items.map((document) =>
        document.id === documentId ? { ...document, file, status: "inceleniyor", progress: 55 } : document,
      ),
    );

    const uploaded = await uploadDocument(target, file);
    setDocuments((items) => items.map((document) => (document.id === documentId ? uploaded : document)));
    showToast(`${target.name} yüklendi.`);
  }

  async function handleStartAnalysis() {
    if (!requiredDocumentsReady) {
      setDocuments((items) => items.map((document) => (document.id === "kvkk" || document.file ? document : { ...document, status: "eksik" })));
      showToast("Analiz için kimlik, gelir belgesi ve banka dökümü yüklenmeli.");
      onNavigate("new-application");
      return;
    }

    setAnalysisLoading(true);
    onNavigate("analysis-process");

    for (let index = 0; index < baseStages.length; index += 1) {
      setStages((items) =>
        items.map((stage, stageIndex) => ({
          ...stage,
          status: stageIndex < index ? "tamamlandi" : stageIndex === index ? "calisiyor" : "bekliyor",
        })),
      );
      await wait(650);
    }

    setStages((items) => items.map((stage) => ({ ...stage, status: "tamamlandi" })));

    try {
      const result = await startBackendAnalysis(form, documents);
      setAnalysisResult(result);
      showToast("AI analiz süreci tamamlandı.");
    } catch {
      setAnalysisResult(demoAnalysisResult);
      showToast("Backend yanıtı alınamadı, demo analiz sonucu gösteriliyor.");
    }

    setAnalysisLoading(false);
    onNavigate("analysis-results");
  }

  async function handleAssistantSend(message: string) {
    if (!message.trim()) return;

    const userMessage: AssistantMessage = { id: `u-${Date.now()}`, sender: "user", text: message };
    setAssistantMessages((items) => [...items, userMessage]);

    const answer = await sendAssistantMessage(paymentPlan.loan_id, message);
    const assistantMessage: AssistantMessage = { id: `a-${Date.now()}`, sender: "assistant", text: answer };
    setAssistantMessages((items) => [...items, assistantMessage]);
  }

  const result = analysisResult || demoAnalysisResult;

  if (activeView === "customer-home") {
    return <CustomerHome result={result} documents={documents} paymentPlan={paymentPlan} onNavigate={onNavigate} />;
  }
  if (activeView === "new-application") {
    return (
      <NewApplication
        documents={documents}
        form={form}
        onFormChange={setForm}
        onStartAnalysis={handleStartAnalysis}
        onUpload={handleUpload}
        requiredDocumentsReady={requiredDocumentsReady}
      />
    );
  }
  if (activeView === "documents") {
    return <DocumentsView documents={documents} onUpload={handleUpload} />;
  }
  if (activeView === "analysis-process") {
    return <AnalysisProcess stages={stages} loading={analysisLoading} onStartAnalysis={handleStartAnalysis} />;
  }
  if (activeView === "analysis-results") {
    return <AnalysisResults result={analysisResult} onNavigate={onNavigate} />;
  }
  if (activeView === "bank-approval") {
    return <BankApproval result={analysisResult} paymentPlan={paymentPlan} onNavigate={onNavigate} />;
  }
  if (activeView === "payment-plan") {
    return <PaymentPlanView paymentPlan={paymentPlan} />;
  }
  if (activeView === "assistant") {
    return <AssistantView messages={assistantMessages} onSend={handleAssistantSend} paymentPlan={paymentPlan} />;
  }
  return <ProfileView />;
}

function CustomerHome({
  result,
  documents,
  paymentPlan,
  onNavigate,
}: {
  result: AnalysisResult;
  documents: UploadedDocument[];
  paymentPlan: PaymentPlan;
  onNavigate: (view: CustomerView) => void;
}) {
  const uploadedCount = documents.filter((document) => document.status === "yuklendi").length;
  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_380px]">
      <Card className="min-h-[360px]">
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Müşteri Portalı</p>
        <h2 className="mt-3 font-display text-4xl font-bold">Başvuru durumunuz kontrol altında</h2>
        <p className="mt-4 max-w-2xl text-muted">
          AI analizleri karar destek amacıyla çalışır. Nihai kredi kararı banka uzmanı ve banka onayı ile kesinleşir.
        </p>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          <MetricCard label="Kredi Uygunluk Skoru" value={result.eligibilityScore} hint="Müşteri görünümü" />
          <MetricCard label="Başvuru Durumu" value="Uzman İncelemesi" tone="green" />
          <MetricCard label="Yüklenen Belge" value={`${uploadedCount}/4`} tone="neutral" />
        </div>
        <div className="mt-8 flex flex-wrap gap-3">
          <button className="gold-gradient rounded-lg px-5 py-3 font-bold text-black" onClick={() => onNavigate("new-application")} type="button">
            Yeni başvuruya git
          </button>
          <button className="rounded-lg border border-white/10 px-5 py-3 text-muted" onClick={() => onNavigate("analysis-results")} type="button">
            Analiz sonucunu görüntüle
          </button>
        </div>
      </Card>
      <Card>
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Ödeme Özeti</p>
        <strong className="mt-4 block font-display text-3xl text-primary">{formatCurrency(paymentPlan.remaining_principal)}</strong>
        <span className="mt-1 block text-sm text-muted">Kalan ana para</span>
        <div className="mt-6 h-2 overflow-hidden rounded-full bg-white/10">
          <i className="block h-full w-2/3 rounded-full bg-secondary" />
        </div>
        <button className="gold-gradient mt-8 w-full rounded-lg px-5 py-3 font-bold text-black" onClick={() => onNavigate("payment-plan")} type="button">
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
  requiredDocumentsReady,
}: {
  documents: UploadedDocument[];
  form: ApplicationForm;
  onFormChange: (form: ApplicationForm) => void;
  onStartAnalysis: () => void;
  onUpload: (documentId: string, file: File) => void;
  requiredDocumentsReady: boolean;
}) {
  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_0.86fr]">
      <Card>
        <div className="mb-5">
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Yeni Başvuru</p>
          <h2 className="mt-2 font-display text-3xl font-bold">Belge yükleme</h2>
          <p className="mt-2 text-sm text-muted">Kimlik, gelir belgesi ve banka dökümü zorunludur. Dosyalar backend analizine PDF olarak gönderilir.</p>
        </div>
        <div className="grid gap-4">
          {documents.map((document) => (
            <UploadCard document={document} key={document.id} onUpload={onUpload} />
          ))}
        </div>
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
        <button className="gold-gradient mt-6 w-full rounded-lg px-5 py-3 font-bold text-black disabled:opacity-60" onClick={onStartAnalysis} type="button">
          {requiredDocumentsReady ? "AI analiz sürecini başlat" : "Belgeleri yükle ve analizi başlat"}
        </button>
      </Card>
    </div>
  );
}

function DocumentsView({ documents, onUpload }: { documents: UploadedDocument[]; onUpload: (documentId: string, file: File) => void }) {
  return (
    <Card>
      <div className="mb-5 flex items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Belgelerim</p>
          <h2 className="mt-2 font-display text-3xl font-bold">Yüklenen PDF belgeleri</h2>
        </div>
        <StatusBadge tone="gold">Servis bağlantısı hazır</StatusBadge>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {documents.map((document) => (
          <UploadCard document={document} key={document.id} onUpload={onUpload} />
        ))}
      </div>
    </Card>
  );
}

function AnalysisProcess({ stages, loading, onStartAnalysis }: { stages: AnalysisStage[]; loading: boolean; onStartAnalysis: () => void }) {
  return (
    <Card>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">AI Analiz Süreci</p>
          <h2 className="mt-2 font-display text-3xl font-bold">Katmanlı analiz akışı</h2>
          <p className="mt-2 text-sm text-muted">Status değerleri backend analiz akışından alınır; bağlantı yoksa demo akış çalışır.</p>
        </div>
        <button className="gold-gradient rounded-lg px-5 py-3 font-bold text-black disabled:opacity-60" disabled={loading} onClick={onStartAnalysis} type="button">
          {loading ? "Analiz sürüyor" : "Analizi başlat"}
        </button>
      </div>
      {loading ? <LoadingState label="Belgeler katmanlı AI mimarisiyle işleniyor" /> : null}
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
  result,
  paymentPlan,
  onNavigate,
}: {
  result: AnalysisResult | null;
  paymentPlan: PaymentPlan;
  onNavigate: (view: CustomerView) => void;
}) {
  if (!result) {
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

  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <Card>
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Banka Onayı</p>
        <h2 className="mt-2 font-display text-3xl font-bold">Başvuru durumu</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <MetricCard label="AI Önerisi" value="Manuel İnceleme" />
          <MetricCard label="Banka Onayı" value="Onaylandı" tone="green" />
          <MetricCard label="Onaylanan Tutar" value={formatCurrency(paymentPlan.approved_amount)} />
          <MetricCard label="Vade" value={`${paymentPlan.maturity_months} Ay`} tone="neutral" />
        </div>
        <p className="mt-6 rounded-xl border border-primary/20 bg-primary/10 p-4 text-sm text-muted">
          {result.aiRecommendation} Nihai karar banka onayıyla gösterilir.
        </p>
      </Card>
      <Card>
        <ChartCard />
      </Card>
    </div>
  );
}

function PaymentPlanView({ paymentPlan }: { paymentPlan: PaymentPlan }) {
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
}: {
  messages: AssistantMessage[];
  onSend: (message: string) => void;
  paymentPlan: PaymentPlan;
}) {
  const [message, setMessage] = useState("");

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
          onSubmit={(event) => {
            event.preventDefault();
            onSend(message);
            setMessage("");
          }}
        >
          <input
            className="rounded-lg border border-white/10 bg-black/30 px-4 py-3 outline-none focus:border-primary/60"
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Asistana ödeme planınızla ilgili soru sorun"
            value={message}
          />
          <button className="gold-gradient rounded-lg px-5 py-3 font-bold text-black" type="submit">
            Gönder
          </button>
        </form>
      </Card>
      <Card>
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Kredi Özeti</p>
        <strong className="mt-4 block font-display text-3xl text-primary">{formatCurrency(paymentPlan.remaining_principal)}</strong>
        <span className="text-sm text-muted">Toplam kalan borç</span>
        <div className="mt-8 grid gap-3">
          {["Kalan borcum ne kadar?", "Erken kapama yapabilir miyim?", "Gecikmiş ödemem var mı?"].map((question) => (
            <button className="rounded-lg border border-white/10 bg-white/[0.04] px-4 py-3 text-left text-muted hover:border-primary/40" key={question} onClick={() => onSend(question)} type="button">
              {question}
            </button>
          ))}
        </div>
      </Card>
    </div>
  );
}

function ProfileView() {
  return (
    <Card>
      <EmptyState title="Profil ekranı hazır" description="Kimlik, iletişim ve bildirim tercihleri backend kullanıcı servisi eklendiğinde burada yönetilecek." />
    </Card>
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

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
