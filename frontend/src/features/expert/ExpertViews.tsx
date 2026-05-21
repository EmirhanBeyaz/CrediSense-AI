"use client";

import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { ProfileAvatar } from "@/components/ui/ProfileAvatar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { demoApplications } from "@/lib/demoData";
import { formatCurrency, scorePercent } from "@/lib/format";
import { fileToProfileImage } from "@/lib/profileImage";
import { updateCurrentProfile } from "@/services/authService";
import {
  approveApplication,
  createExpertReport,
  type CreditOfferInput,
  getApplicationDocumentBlobUrl,
  getApplicationDocuments,
  getExpertApplications,
  rejectApplication,
  requestExtraDocument,
  reviseApplication,
} from "@/services/expertService";
import { getReports } from "@/services/reportService";
import type { ApplicationDocument, ApplicationRecord, ExpertView, ReportSummary, User } from "@/types";

type ExpertViewsProps = {
  activeView: ExpertView;
  onUserUpdate: (user: User) => void;
  showToast: (message: string) => void;
  user: User;
};

type ExpertDecision = "approve" | "revise" | "extra" | "reject";
type CreditOfferForm = {
  approvedAmount: string;
  termMonths: string;
  monthlyInterestRate: string;
};

const extraDocumentOptions = [
  "Güncel gelir belgesi",
  "Son 6 aylık hesap dökümü",
];

export function ExpertViews({ activeView, onUserUpdate, showToast, user }: ExpertViewsProps) {
  const [applications, setApplications] = useState<ApplicationRecord[]>(demoApplications);
  const [selectedId, setSelectedId] = useState(demoApplications[0].application_id);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [selectedDocuments, setSelectedDocuments] = useState<ApplicationDocument[]>([]);
  const [decisionNote, setDecisionNote] = useState("");
  const [extraDocumentText, setExtraDocumentText] = useState("Güncel gelir belgesi");
  const [reportText, setReportText] = useState("");
  const [profileImageLoading, setProfileImageLoading] = useState(false);
  const [creditOffer, setCreditOffer] = useState<CreditOfferForm>(() => defaultCreditOfferForm(demoApplications[0]));

  useEffect(() => {
    refreshExpertData();
  }, [activeView]);

  const selected = useMemo(
    () => applications.find((application) => application.application_id === selectedId) || applications[0] || demoApplications[0],
    [applications, selectedId],
  );
  const manualApplications = useMemo(() => applications.filter(isManualReview), [applications]);

  useEffect(() => {
    setCreditOffer(defaultCreditOfferForm(selected));
  }, [selected?.application_id]);

  useEffect(() => {
    if (!selected?.application_id) {
      setSelectedDocuments([]);
      return;
    }

    let cancelled = false;
    getApplicationDocuments(selected.application_id)
      .then((documents) => {
        if (!cancelled) {
          setSelectedDocuments(documents);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSelectedDocuments(selected.documents || []);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selected?.application_id, selected?.documents]);

  async function refreshExpertData() {
    setLoading(true);
    try {
      const items = await getExpertApplications();
      const nextItems = items.length ? items : demoApplications;
      setApplications(nextItems);
      setSelectedId((currentId) => nextItems.some((item) => item.application_id === currentId) ? currentId : nextItems[0].application_id);
      setReports(await getReports());
    } catch {
      setApplications(demoApplications);
      showToast("Backend başvuru listesi alınamadı, demo kayıtlar gösteriliyor.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDecision(action: ExpertDecision) {
    if (isDecisionFinal(selected)) {
      showToast("Bu başvuru için final karar verilmiş. Yeni karar girilemez.");
      return;
    }

    setActionLoading(true);
    try {
      const note = decisionNote.trim() || defaultDecisionNote(action, selected);
      const requestedDocuments = parseRequestedDocuments(extraDocumentText);
      let updated: ApplicationRecord;

      if (action === "approve") {
        updated = await approveApplication(
          selected.application_id,
          note,
          shouldAllowCreditOffer(selected) ? creditOfferPayload(creditOffer) : undefined,
        );
      }
      else if (action === "revise") updated = await reviseApplication(selected.application_id, note);
      else if (action === "extra") updated = await requestExtraDocument(selected.application_id, requestedDocuments, note);
      else updated = await rejectApplication(selected.application_id, note);

      setApplications((items) => replaceApplication(items, updated));
      setSelectedId(updated.application_id);
      setDecisionNote("");
      showToast(decisionToast(action));
      refreshExpertData();
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Karar backend'e gönderilemedi.");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleSaveReport() {
    if (reportText.trim().length < 20) {
      showToast("Kanaat raporu en az 20 karakter olmalı.");
      return;
    }

    setActionLoading(true);
    try {
      const report = await createExpertReport(
        selected.application_id,
        `Uzman kanaat raporu - ${selected.customer_name}`,
        reportText,
      );
      setReports((items) => [report, ...items]);
      setApplications((items) =>
        items.map((application) =>
          application.application_id === selected.application_id
            ? { ...application, report_count: (application.report_count || 0) + 1 }
            : application,
        ),
      );
      setReportText("");
      showToast("Uzman kanaat raporu raporlar sekmesine kaydedildi.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Kanaat raporu kaydedilemedi.");
    } finally {
      setActionLoading(false);
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

  if (loading && applications.length === 0) {
    return <LoadingState label="Başvurular yükleniyor" />;
  }

  if (activeView === "expert-home") {
    return <ExpertHome applications={applications} />;
  }
  if (activeView === "application-queue") {
    return (
      <ApplicationQueueView
        applications={applications}
        onReportTextChange={setReportText}
        onSaveReport={handleSaveReport}
        onSelect={setSelectedId}
        reportText={reportText}
        selected={selected}
        selectedId={selectedId}
      />
    );
  }
  if (activeView === "pending-review") {
    return (
      <PendingReviewView
        actionLoading={actionLoading}
        applications={manualApplications}
        decisionNote={decisionNote}
        extraDocumentText={extraDocumentText}
        creditOffer={creditOffer}
        onDecision={handleDecision}
        onCreditOfferChange={setCreditOffer}
        onDecisionNoteChange={setDecisionNote}
        onExtraDocumentTextChange={setExtraDocumentText}
        onReportTextChange={setReportText}
        onSaveReport={handleSaveReport}
        onSelect={setSelectedId}
        reportText={reportText}
        selected={manualApplications.find((application) => application.application_id === selectedId) || manualApplications[0] || selected}
        selectedId={selectedId}
      />
    );
  }
  if (activeView === "document-control") {
    return <DocumentControl documents={selectedDocuments} selected={selected} showToast={showToast} />;
  }
  if (activeView === "risk-analysis") {
    return <RiskAnalysis selected={selected} />;
  }
  if (activeView === "decision-process") {
    return (
      <DecisionProcess
        decisionNote={decisionNote}
        extraDocumentText={extraDocumentText}
        creditOffer={creditOffer}
        loading={actionLoading}
        onDecision={handleDecision}
        onCreditOfferChange={setCreditOffer}
        onDecisionNoteChange={setDecisionNote}
        onExtraDocumentTextChange={setExtraDocumentText}
        selected={selected}
      />
    );
  }
  if (activeView === "reports") {
    return <ReportsView applications={applications} reports={reports} />;
  }
  return (
    <ProfileView
      applications={applications}
      onProfileImageUpload={handleProfileImageUpload}
      profileImageLoading={profileImageLoading}
      reports={reports}
      user={user}
    />
  );
}

function ExpertHome({ applications }: { applications: ApplicationRecord[] }) {
  const autoCount = applications.filter(isAutoPreApproved).length;
  const manualCount = applications.filter(isManualReview).length;
  const highRiskCount = applications.filter((item) => item.risk_level === "Yüksek").length;

  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_420px]">
      <Card>
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Uzman Paneli</p>
        <h2 className="mt-2 font-display text-4xl font-bold">Banka uzman çalışma alanı</h2>
        <p className="mt-4 max-w-2xl text-muted">
          Düşük riskli başvurular sistem tarafından otomatik ön onaya ayrılır. Orta ve yüksek riskli başvurularda nihai karar banka uzmanına bırakılır.
        </p>
        <div className="mt-8 grid gap-4 md:grid-cols-4">
          <MetricCard label="Toplam Başvuru" value={applications.length} />
          <MetricCard label="Otomatik Ön Onay" value={autoCount} tone="green" />
          <MetricCard label="Manuel İnceleme" value={manualCount} />
          <MetricCard label="Yüksek Risk" value={highRiskCount} tone="red" />
        </div>
      </Card>
      <Card>
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">İş Akışı Mantığı</p>
        <div className="mt-5 grid gap-3 text-sm text-muted">
          <WorkflowLine title="Düşük risk" text="Sistem otomatik ön onay verir, uzman sadece izleyebilir." tone="green" />
          <WorkflowLine title="Orta risk" text="Uzman kanaati ve karar süreci gerekir." tone="gold" />
          <WorkflowLine title="Yüksek risk" text="Detaylı inceleme, ek belge veya ret aksiyonu beklenir." tone="red" />
        </div>
      </Card>
    </div>
  );
}

function ApplicationQueueView({
  applications,
  selected,
  selectedId,
  reportText,
  onSelect,
  onReportTextChange,
  onSaveReport,
}: {
  applications: ApplicationRecord[];
  selected: ApplicationRecord;
  selectedId: string;
  reportText: string;
  onSelect: (id: string) => void;
  onReportTextChange: (value: string) => void;
  onSaveReport: () => void;
}) {
  const autoApplications = applications.filter(isAutoPreApproved);
  const manualApplications = applications.filter(isManualReview);

  if (!applications.length) {
    return <EmptyState title="Başvuru yok" description="Backend başvuru deposunda kayıt bulunamadı." />;
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_440px]">
      <Card>
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Başvuru Kuyruğu</p>
            <h2 className="mt-2 font-display text-3xl font-bold">Otomatik ayrıştırma kuyruğu</h2>
            <p className="mt-2 text-sm text-muted">Bu ekran başvuruları ilk sistem kararına göre ayırır; manuel karar ekranı değildir.</p>
          </div>
          <StatusBadge tone="gold">Backend /applications</StatusBadge>
        </div>

        <QueueSection
          applications={autoApplications}
          emptyText="Düşük riskli otomatik ön onay kaydı yok."
          onSelect={onSelect}
          selectedId={selectedId}
          title="Sistem tarafından otomatik ön onaylananlar"
        />
        <div className="mt-6">
          <QueueSection
            applications={manualApplications}
            emptyText="Uzman kararı bekleyen orta/yüksek riskli kayıt yok."
            onSelect={onSelect}
            selectedId={selectedId}
            title="Uzman kararı bekleyenler"
          />
        </div>
      </Card>
      <ApplicationDetail
        onReportTextChange={onReportTextChange}
        onSaveReport={onSaveReport}
        reportText={reportText}
        selected={selected}
      />
    </div>
  );
}

function PendingReviewView({
  applications,
  selected,
  selectedId,
  actionLoading,
  decisionNote,
  extraDocumentText,
  creditOffer,
  reportText,
  onSelect,
  onDecision,
  onCreditOfferChange,
  onDecisionNoteChange,
  onExtraDocumentTextChange,
  onReportTextChange,
  onSaveReport,
}: {
  applications: ApplicationRecord[];
  selected: ApplicationRecord;
  selectedId: string;
  actionLoading: boolean;
  decisionNote: string;
  extraDocumentText: string;
  creditOffer: CreditOfferForm;
  reportText: string;
  onSelect: (id: string) => void;
  onDecision: (decision: ExpertDecision) => void;
  onCreditOfferChange: (value: CreditOfferForm) => void;
  onDecisionNoteChange: (value: string) => void;
  onExtraDocumentTextChange: (value: string) => void;
  onReportTextChange: (value: string) => void;
  onSaveReport: () => void;
}) {
  if (!applications.length) {
    return <EmptyState title="İnceleme bekleyen başvuru yok" description="Orta veya yüksek riskli manuel karar kaydı oluştuğunda burada listelenir." />;
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
      <Card>
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">İnceleme Bekleyenler</p>
        <h2 className="mt-2 font-display text-3xl font-bold">Manuel karar gerektirenler</h2>
        <p className="mt-2 text-sm text-muted">Bu liste düşük riskli otomatik ön onay kayıtlarını göstermez.</p>
        <div className="mt-6 grid gap-3">
          {applications.map((application) => (
            <ApplicationRow application={application} key={application.application_id} onSelect={onSelect} selected={selectedId === application.application_id} />
          ))}
        </div>
      </Card>
      <div className="grid gap-5">
        <ApplicationDetail
          onReportTextChange={onReportTextChange}
          onSaveReport={onSaveReport}
          reportText={reportText}
          selected={selected}
        />
        <DecisionControls
          decisionNote={decisionNote}
          extraDocumentText={extraDocumentText}
          creditOffer={creditOffer}
          loading={actionLoading}
          onDecision={onDecision}
          onCreditOfferChange={onCreditOfferChange}
          onDecisionNoteChange={onDecisionNoteChange}
          onExtraDocumentTextChange={onExtraDocumentTextChange}
          selected={selected}
        />
      </div>
    </div>
  );
}

function QueueSection({
  title,
  applications,
  selectedId,
  emptyText,
  onSelect,
}: {
  title: string;
  applications: ApplicationRecord[];
  selectedId: string;
  emptyText: string;
  onSelect: (id: string) => void;
}) {
  return (
    <section>
      <h3 className="mb-3 font-display text-xl font-bold">{title}</h3>
      <div className="grid gap-3">
        {applications.length ? applications.map((application) => (
          <ApplicationRow application={application} key={application.application_id} onSelect={onSelect} selected={selectedId === application.application_id} />
        )) : (
          <div className="rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-muted">{emptyText}</div>
        )}
      </div>
    </section>
  );
}

function ApplicationRow({
  application,
  selected,
  onSelect,
}: {
  application: ApplicationRecord;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      className={`grid grid-cols-[1fr_auto_auto] items-center gap-3 rounded-xl border p-4 text-left transition ${
        selected ? "border-primary/50 bg-primary/10" : "border-white/10 bg-black/25 hover:border-primary/30"
      }`}
      onClick={() => onSelect(application.application_id)}
      type="button"
    >
      <div>
        <strong>{application.customer_name}</strong>
        <span className="mt-1 block text-sm text-muted">{application.application_id}</span>
      </div>
      <span className="text-muted">{application.review_route_text || application.status}</span>
      <StatusBadge tone={riskTone(application)}>{application.risk_level || "Orta"}</StatusBadge>
    </button>
  );
}

function ApplicationDetail({
  selected,
  reportText,
  onReportTextChange,
  onSaveReport,
}: {
  selected: ApplicationRecord;
  reportText: string;
  onReportTextChange: (value: string) => void;
  onSaveReport: () => void;
}) {
  return (
    <Card>
      <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Başvuru Detayı</p>
      <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-3xl font-bold">{selected.customer_name}</h2>
          <p className="mt-1 text-sm text-muted">{selected.application_id}</p>
        </div>
        <StatusBadge tone={routeTone(selected)}>{selected.review_route_text || selected.status}</StatusBadge>
      </div>

      <p className="mt-5 rounded-xl border border-primary/20 bg-primary/10 p-4 text-sm text-muted">
        {selected.system_action || selected.ai_recommendation}
      </p>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <MetricCard label="Risk Skoru" value={selected.risk_score || 0} tone={riskTone(selected)} />
        <MetricCard label="Belge Güveni" value={scorePercent(selected.document_confidence_score || 0)} tone="green" />
        <MetricCard label="Tutarlılık" value={scorePercent(selected.consistency_score || 0)} />
      </div>

      <div className="mt-5 grid gap-3 rounded-xl border border-white/10 bg-black/25 p-4 text-sm text-muted md:grid-cols-2">
        <DetailLine label="Talep edilen kredi" value={formatCreditValue(selected.credit_request?.requested_amount)} />
        <DetailLine label="Vade" value={selected.credit_request?.term_months ? `${selected.credit_request.term_months} Ay` : "Belirtilmedi"} />
        <DetailLine label="Beyan edilen gelir" value={formatCreditValue(selected.credit_request?.declared_monthly_income)} />
        <DetailLine label="Mevcut borç" value={formatCreditValue(selected.credit_request?.current_total_debt)} />
      </div>

      {selected.requested_documents?.length ? (
        <div className="mt-5 rounded-xl border border-primary/20 bg-primary/10 p-4 text-sm">
          <strong>İstenen ek belgeler</strong>
          <ul className="mt-2 grid gap-1 text-muted">
            {selected.requested_documents.map((document) => <li key={document}>{document}</li>)}
          </ul>
        </div>
      ) : null}

      <div className="mt-5">
        <label className="grid gap-2 text-sm text-muted">
          Uzman kanaat raporu
          <textarea
            className="min-h-[130px] rounded-xl border border-white/10 bg-black/30 p-4 text-white outline-none focus:border-primary/60"
            onChange={(event) => onReportTextChange(event.target.value)}
            placeholder="Başvuru sahibinin gelir, belge tutarlılığı ve risk göstergelerine göre uzman kanaatinizi yazın."
            value={reportText}
          />
        </label>
        <button className="gold-gradient mt-3 rounded-lg px-5 py-3 font-bold text-black" onClick={onSaveReport} type="button">
          Kanaat raporunu kaydet
        </button>
        <span className="ml-3 text-sm text-muted">Kayıtlı rapor: {selected.report_count || 0}</span>
      </div>
    </Card>
  );
}

function DocumentControl({
  selected,
  documents,
  showToast,
}: {
  selected: ApplicationRecord;
  documents: ApplicationDocument[];
  showToast: (message: string) => void;
}) {
  const [activeDocumentId, setActiveDocumentId] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    setActiveDocumentId((currentId) => {
      if (documents.some((document) => document.document_id === currentId)) {
        return currentId;
      }
      return documents[0]?.document_id || "";
    });
  }, [documents]);

  useEffect(() => {
    if (!activeDocumentId) {
      setPreviewUrl("");
      return;
    }

    let cancelled = false;
    let objectUrl = "";
    setPreviewLoading(true);
    getApplicationDocumentBlobUrl(activeDocumentId)
      .then((url) => {
        objectUrl = url;
        if (cancelled) {
          URL.revokeObjectURL(url);
        } else {
          setPreviewUrl(url);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setPreviewUrl("");
          showToast(error instanceof Error ? error.message : "Belge görüntülenemedi.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setPreviewLoading(false);
        }
      });

    return () => {
      cancelled = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [activeDocumentId, showToast]);

  const activeDocument = documents.find((document) => document.document_id === activeDocumentId) || documents[0];

  return (
    <div className="grid gap-5 xl:grid-cols-3">
      <Card>
        <MetricCard label="Belge Güven Skoru" value={scorePercent(selected.document_confidence_score || 0.95)} tone="green" />
      </Card>
      <Card>
        <MetricCard label="Tutarlılık Skoru" value={scorePercent(selected.consistency_score || 0.82)} />
      </Card>
      <Card>
        <MetricCard label="Anomali Skoru" value={scorePercent(selected.anomaly_score || 0.25)} tone="red" />
      </Card>
      <RiskReviewPanel selected={selected} />
      <Card className="xl:col-span-3">
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Belge Kontrolü</p>
        <h2 className="mt-2 font-display text-3xl font-bold">{selected.customer_name}</h2>
        <div className="mt-6 grid gap-4 lg:grid-cols-[320px_1fr]">
          <div className="grid content-start gap-3">
            {documents.length ? documents.map((document) => (
              <button
                className={`rounded-xl border p-4 text-left transition ${
                  activeDocumentId === document.document_id ? "border-primary/50 bg-primary/10" : "border-white/10 bg-black/25 hover:border-primary/30"
                }`}
                key={document.document_id}
                onClick={() => setActiveDocumentId(document.document_id)}
                type="button"
              >
                <span className="material-symbols-outlined mb-3 text-primary">description</span>
                <strong className="block">{document.document_name || documentLabel(document.document_type)}</strong>
                <small className="mt-1 block text-muted">{document.original_file_name || document.document_id}</small>
                <StatusBadge tone="green">{document.status || "Yüklendi"}</StatusBadge>
              </button>
            )) : (
              <div className="rounded-xl border border-white/10 bg-black/25 p-4">
                <EmptyState title="Belge bulunamadı" description="Bu başvuruya bağlı yüklenen PDF kaydı henüz yok." />
              </div>
            )}
          </div>

          <div className="min-h-[520px] rounded-xl border border-white/10 bg-black/25 p-3">
            {previewLoading ? (
              <LoadingState label="Belge görüntüleniyor" />
            ) : previewUrl && activeDocument ? (
              <iframe
                className="h-[520px] w-full rounded-lg border-0 bg-white"
                src={previewUrl}
                title={activeDocument.document_name || activeDocument.original_file_name || "Başvuru belgesi"}
              />
            ) : (
              <div className="grid h-[520px] place-items-center">
                <EmptyState title="Önizleme bekleniyor" description="Listeden bir PDF seçildiğinde burada görüntülenir." />
              </div>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}

function RiskReviewPanel({ selected }: { selected: ApplicationRecord }) {
  const review = buildRiskReviewDetails(selected);
  if (!review.shouldShow) {
    return null;
  }

  return (
    <Card className="xl:col-span-3">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Risk Gerekçeleri</p>
          <h2 className="mt-2 font-display text-2xl font-bold">Uzman karar odağı</h2>
          <p className="mt-2 max-w-3xl text-sm text-muted">{review.summary}</p>
        </div>
        <StatusBadge tone={review.tone}>{review.badge}</StatusBadge>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        <RiskDetailColumn title="Ana risk sinyalleri" items={review.riskSignals} />
        <RiskDetailColumn title="Belge ve veri uyarıları" items={review.documentFindings} />
        <RiskDetailColumn title="Karar verirken kontrol et" items={review.reviewFocus} />
      </div>
    </Card>
  );
}

function RiskDetailColumn({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/25 p-4">
      <strong className="block text-sm">{title}</strong>
      <ul className="mt-3 grid gap-2 text-sm text-muted">
        {items.map((item) => (
          <li className="rounded-lg border border-white/10 bg-white/[0.03] p-3" key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function RiskAnalysis({ selected }: { selected: ApplicationRecord }) {
  return (
    <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
      <Card className="text-center">
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Risk Skoru</p>
        <div className="mx-auto mt-8 grid h-44 w-44 place-items-center rounded-full border-[12px] border-primary/80 bg-primary/10 shadow-glow">
          <strong className="font-display text-5xl text-primary">{selected.risk_score || 0}</strong>
        </div>
        <h2 className="mt-7 font-display text-2xl font-bold">{selected.risk_level || "Orta"} risk</h2>
      </Card>
      <Card>
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">AI Önerisi</p>
        <h2 className="mt-2 font-display text-3xl font-bold">Karar destek açıklaması</h2>
        <p className="mt-5 rounded-xl border border-primary/20 bg-primary/10 p-4 text-muted">{selected.ai_recommendation}</p>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <MetricCard label="Belge Güveni" value={scorePercent(selected.document_confidence_score || 0.95)} tone="green" />
          <MetricCard label="Tutarlılık" value={scorePercent(selected.consistency_score || 0.82)} />
          <MetricCard label="Anomali" value={scorePercent(selected.anomaly_score || 0.25)} tone="red" />
        </div>
        {selected.reasons?.length ? (
          <ul className="mt-6 grid gap-2 text-sm text-muted">
            {selected.reasons.map((reason) => <li className="rounded-lg border border-white/10 bg-black/20 p-3" key={reason}>{reason}</li>)}
          </ul>
        ) : null}
      </Card>
    </div>
  );
}

function DecisionProcess({
  selected,
  loading,
  decisionNote,
  extraDocumentText,
  creditOffer,
  onDecision,
  onCreditOfferChange,
  onDecisionNoteChange,
  onExtraDocumentTextChange,
}: {
  selected: ApplicationRecord;
  loading: boolean;
  decisionNote: string;
  extraDocumentText: string;
  creditOffer: CreditOfferForm;
  onDecision: (decision: ExpertDecision) => void;
  onCreditOfferChange: (value: CreditOfferForm) => void;
  onDecisionNoteChange: (value: string) => void;
  onExtraDocumentTextChange: (value: string) => void;
}) {
  return (
    <Card>
      <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Karar Süreci</p>
      <h2 className="mt-2 font-display text-3xl font-bold">{selected.customer_name}</h2>
      <DecisionControls
        decisionNote={decisionNote}
        extraDocumentText={extraDocumentText}
        creditOffer={creditOffer}
        loading={loading}
        onDecision={onDecision}
        onCreditOfferChange={onCreditOfferChange}
        onDecisionNoteChange={onDecisionNoteChange}
        onExtraDocumentTextChange={onExtraDocumentTextChange}
        selected={selected}
      />
    </Card>
  );
}

function DecisionControls({
  selected,
  loading,
  decisionNote,
  extraDocumentText,
  creditOffer,
  onDecision,
  onCreditOfferChange,
  onDecisionNoteChange,
  onExtraDocumentTextChange,
}: {
  selected: ApplicationRecord;
  loading: boolean;
  decisionNote: string;
  extraDocumentText: string;
  creditOffer: CreditOfferForm;
  onDecision: (decision: ExpertDecision) => void;
  onCreditOfferChange: (value: CreditOfferForm) => void;
  onDecisionNoteChange: (value: string) => void;
  onExtraDocumentTextChange: (value: string) => void;
}) {
  const finalStatus = isDecisionFinal(selected);
  const requestedDocuments = parseRequestedDocuments(extraDocumentText);
  const offerEditable = shouldAllowCreditOffer(selected);
  const suggestedMonthlyRate = suggestedMonthlyInterestRate(selected);

  function handleRequestedDocumentToggle(documentName: string) {
    const nextDocuments = requestedDocuments.includes(documentName)
      ? requestedDocuments.filter((item) => item !== documentName)
      : [...requestedDocuments, documentName];

    if (!nextDocuments.length) {
      return;
    }

    onExtraDocumentTextChange(nextDocuments.join(", "));
  }

  function updateCreditOffer(field: keyof CreditOfferForm, value: string) {
    onCreditOfferChange({ ...creditOffer, [field]: value });
  }

  return (
    <div className="mt-6 grid gap-4">
      <label className="grid gap-2 text-sm text-muted">
        Karar notu
        <textarea
          className="min-h-[90px] rounded-xl border border-white/10 bg-black/30 p-4 text-white outline-none focus:border-primary/60"
          onChange={(event) => onDecisionNoteChange(event.target.value)}
          placeholder="Karar gerekçesini veya müşteriye iletilecek notu yazın."
          value={decisionNote}
        />
      </label>
      <fieldset className="grid gap-3">
        <legend className="text-sm text-muted">Ek belge adları</legend>
        <div className="grid gap-3 md:grid-cols-2">
          {extraDocumentOptions.map((documentName) => {
            const selectedDocument = requestedDocuments.includes(documentName);
            return (
              <label
                className={`flex min-h-14 cursor-pointer items-center gap-3 rounded-lg border px-4 py-3 text-sm font-semibold transition ${
                  selectedDocument
                    ? "border-primary/60 bg-primary/10 text-primary"
                    : "border-white/10 bg-black/30 text-muted hover:border-primary/40 hover:text-white"
                }`}
                key={documentName}
              >
                <input
                  checked={selectedDocument}
                  className="h-4 w-4 accent-yellow-400"
                  onChange={() => handleRequestedDocumentToggle(documentName)}
                  type="checkbox"
                />
                <span>{documentName}</span>
              </label>
            );
          })}
        </div>
      </fieldset>
      {offerEditable ? (
        <section className="grid gap-4 rounded-xl border border-primary/20 bg-primary/10 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.14em] text-primary">Kredi koşul teklifi</p>
              <h3 className="mt-1 font-display text-xl font-bold">Orta/yüksek risk için uzman limiti</h3>
            </div>
            <StatusBadge tone={selected.risk_level === "Yüksek" ? "red" : "gold"}>
              {`Sistem önerisi %${(suggestedMonthlyRate * 100).toFixed(2)}`}
            </StatusBadge>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <label className="grid gap-2 text-sm text-muted">
              Verilebilecek en yüksek kredi
              <input
                className="rounded-lg border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-primary/60"
                inputMode="decimal"
                onChange={(event) => updateCreditOffer("approvedAmount", event.target.value)}
                value={creditOffer.approvedAmount}
              />
            </label>
            <label className="grid gap-2 text-sm text-muted">
              Vade
              <input
                className="rounded-lg border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-primary/60"
                inputMode="numeric"
                onChange={(event) => updateCreditOffer("termMonths", event.target.value)}
                value={creditOffer.termMonths}
              />
            </label>
            <label className="grid gap-2 text-sm text-muted">
              Aylık faiz %
              <input
                className="rounded-lg border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-primary/60"
                inputMode="decimal"
                onChange={(event) => updateCreditOffer("monthlyInterestRate", event.target.value)}
                value={creditOffer.monthlyInterestRate}
              />
            </label>
          </div>
          <p className="text-xs text-muted">Ürün bandı aylık %1,85 - %4,25. Onaylandığında ödeme planı bu koşullarla oluşur.</p>
        </section>
      ) : null}
      <div className="grid gap-4 md:grid-cols-4">
        <button className="gold-gradient rounded-lg px-5 py-4 font-bold text-black disabled:opacity-60" disabled={loading || finalStatus} onClick={() => onDecision("approve")} type="button">
          Onayla
        </button>
        <button className="rounded-lg border border-white/10 bg-white/[0.04] px-5 py-4 font-bold disabled:opacity-60" disabled={loading || finalStatus} onClick={() => onDecision("revise")} type="button">
          Revize Et
        </button>
        <button className="rounded-lg border border-primary/30 bg-primary/10 px-5 py-4 font-bold text-primary disabled:opacity-60" disabled={loading || finalStatus} onClick={() => onDecision("extra")} type="button">
          Ek Belge İste
        </button>
        <button className="rounded-lg border border-danger/30 bg-danger/10 px-5 py-4 font-bold text-danger disabled:opacity-60" disabled={loading || finalStatus} onClick={() => onDecision("reject")} type="button">
          Reddet
        </button>
      </div>
      {finalStatus ? (
        <p className="rounded-lg border border-white/10 bg-white/[0.03] p-3 text-sm text-muted">
          Bu başvuruda karar süreci tamamlandı. Yeni aksiyon girilemez.
        </p>
      ) : null}
      {loading ? <LoadingState label="Karar backend servisine gönderiliyor" /> : null}
    </div>
  );
}

function ReportsView({
  applications,
  reports,
}: {
  applications: ApplicationRecord[];
  reports: ReportSummary[];
}) {
  const [selectedReportId, setSelectedReportId] = useState(reports[0]?.id || "");
  const selectedReport = reports.find((report) => report.id === selectedReportId) || reports[0] || null;
  const selectedApplication = selectedReport?.applicationId
    ? applications.find((application) => application.application_id === selectedReport.applicationId)
    : null;
  const completedApplications = applications.filter(isDecisionFinal);
  const pendingApplications = applications.filter((application) => !isDecisionFinal(application) && isManualReview(application));
  const untouchedApplications = applications.filter((application) => !isDecisionFinal(application) && !isManualReview(application));

  useEffect(() => {
    if (!reports.length) {
      setSelectedReportId("");
      return;
    }
    setSelectedReportId((currentId) => reports.some((report) => report.id === currentId) ? currentId : reports[0].id);
  }, [reports]);

  return (
    <div className="grid gap-5">
      <div className="grid gap-4 xl:grid-cols-3">
        <ApplicationStatusPanel applications={completedApplications} emptyText="Tamamlanan başvuru yok." title="Tamamlanmış başvurular" tone="green" />
        <ApplicationStatusPanel applications={untouchedApplications} emptyText="İşlem bekleyen yeni kayıt yok." title="Henüz işlem yapılmamış" tone="neutral" />
        <ApplicationStatusPanel applications={pendingApplications} emptyText="Bekleyen manuel karar yok." title="Beklemede" tone="gold" />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_420px]">
        <Card>
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Raporlar</p>
          <h2 className="mt-2 font-display text-3xl font-bold">Uzman rapor ekranı</h2>
          {!reports.length ? (
            <div className="mt-6">
              <EmptyState title="Henüz rapor yok" description="Başvuru detayında yazılan kanaat raporları ve analiz raporları burada listelenir." />
            </div>
          ) : (
            <div className="mt-6 grid gap-3">
              {reports.map((report) => {
                const application = report.applicationId
                  ? applications.find((item) => item.application_id === report.applicationId)
                  : null;
                return (
                  <button
                    className={`rounded-xl border p-4 text-left transition ${
                      selectedReport?.id === report.id ? "border-primary/50 bg-primary/10" : "border-white/10 bg-black/25 hover:border-primary/30"
                    }`}
                    key={report.id}
                    onClick={() => setSelectedReportId(report.id)}
                    type="button"
                  >
                    <div className="grid gap-3 md:grid-cols-[1fr_auto_auto] md:items-center">
                      <strong>{report.title}</strong>
                      <span className="text-sm text-muted">{formatDate(report.createdAt)}</span>
                      <StatusBadge tone="gold">{report.type}</StatusBadge>
                    </div>
                    <p className="mt-2 text-sm text-muted">
                      Başvuru: {report.applicationId || "Başvuru bilgisi yok"}
                      {application ? ` - ${application.customer_name}` : ""}
                    </p>
                  </button>
                );
              })}
            </div>
          )}
        </Card>

        <Card>
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Rapor Detayı</p>
          {selectedReport ? (
            <div className="mt-4 grid gap-4">
              <div>
                <h3 className="font-display text-2xl font-bold">{selectedReport.title}</h3>
                <p className="mt-2 text-sm text-muted">{formatDate(selectedReport.createdAt)} · {selectedReport.type}</p>
              </div>
              <div className="rounded-xl border border-white/10 bg-black/25 p-4 text-sm">
                <DetailLine label="Başvuru" value={selectedReport.applicationId || "Bağlı başvuru yok"} />
                <div className="mt-4 grid gap-3">
                  <DetailLine label="Müşteri" value={selectedApplication?.customer_name || "Başvuru kaydı bulunamadı"} />
                  <DetailLine label="Durum" value={selectedApplication?.status || "Durum bilgisi yok"} />
                  <DetailLine label="Risk" value={selectedApplication?.risk_level || "Risk bilgisi yok"} />
                </div>
              </div>
              {selectedReport.content ? (
                <p className="max-h-[260px] overflow-y-auto rounded-lg border border-white/10 bg-white/[0.03] p-3 text-sm text-muted">
                  {selectedReport.content}
                </p>
              ) : (
                <p className="rounded-lg border border-white/10 bg-white/[0.03] p-3 text-sm text-muted">
                  Rapor içeriği dosya olarak kaydedilmiş; bağlı başvuru bilgisi yukarıda gösteriliyor.
                </p>
              )}
            </div>
          ) : (
            <EmptyState title="Rapor seçilmedi" description="Soldaki listeden rapor seçildiğinde bağlı başvuru burada görünür." />
          )}
        </Card>
      </div>
    </div>
  );
}

function ApplicationStatusPanel({
  applications,
  emptyText,
  title,
  tone,
}: {
  applications: ApplicationRecord[];
  emptyText: string;
  title: string;
  tone: "gold" | "green" | "red" | "neutral";
}) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Başvuru Paneli</p>
          <h3 className="mt-2 font-display text-xl font-bold">{title}</h3>
        </div>
        <StatusBadge tone={tone}>{String(applications.length)}</StatusBadge>
      </div>
      <div className="mt-5 grid max-h-64 gap-3 overflow-y-auto pr-2">
        {applications.length ? applications.map((application) => (
          <article className="rounded-lg border border-white/10 bg-black/25 p-3" key={application.application_id}>
            <strong className="block">{application.customer_name}</strong>
            <span className="mt-1 block text-xs text-muted">{application.application_id}</span>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <StatusBadge tone={riskTone(application)}>{application.risk_level || "Risk yok"}</StatusBadge>
              <span className="text-xs text-muted">{application.status}</span>
            </div>
          </article>
        )) : (
          <p className="rounded-lg border border-white/10 bg-black/25 p-3 text-sm text-muted">{emptyText}</p>
        )}
      </div>
    </Card>
  );
}

function ProfileView({
  applications,
  onProfileImageUpload,
  profileImageLoading,
  reports,
  user,
}: {
  applications: ApplicationRecord[];
  onProfileImageUpload: (file: File) => void;
  profileImageLoading: boolean;
  reports: ReportSummary[];
  user: User;
}) {
  const profile = user.profile || {};
  const manualCount = applications.filter(isManualReview).length;
  const completedCount = applications.filter(isDecisionFinal).length;
  const autoCount = applications.filter(isAutoPreApproved).length;

  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
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
              <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Uzman Profili</p>
              <h2 className="mt-2 font-display text-3xl font-bold">{user.fullName}</h2>
              <p className="mt-2 text-muted">{user.title || "Banka uzmanı"}</p>
            </div>
          </div>
          <StatusBadge tone={user.emailVerified ? "green" : "gold"}>
            {user.emailVerified ? "Kurumsal hesap doğrulandı" : "Doğrulama bekliyor"}
          </StatusBadge>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <MetricCard label="Kullanıcı adı" value={user.username || "-"} tone="neutral" />
          <MetricCard label="Departman" value={String(profile.department || "Bireysel kredi risk")} tone="neutral" />
          <MetricCard label="Şube" value={String(profile.branch || "Dijital inceleme")} tone="neutral" />
        </div>

        <div className="mt-6 grid gap-3 rounded-xl border border-white/10 bg-black/25 p-4 text-sm text-muted md:grid-cols-2">
          <DetailLine label="E-posta" value={user.email || "-"} />
          <DetailLine label="Rol" value="Banka uzmanı" />
          <DetailLine label="Yetki kapsamı" value={String(profile.authorization_level || "Kredi başvuru inceleme")} />
          <DetailLine label="Karar limiti" value={String(profile.approval_limit || "Dijital kanal politikası")} />
        </div>
      </Card>

      <Card>
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Operasyon Özeti</p>
        <div className="mt-5 grid gap-4">
          <MetricCard label="Manuel inceleme" value={manualCount} />
          <MetricCard label="Otomatik ön onay" value={autoCount} tone="green" />
          <MetricCard label="Tamamlanan karar" value={completedCount} tone="neutral" />
          <MetricCard label="Kayıtlı rapor" value={reports.length} tone="neutral" />
        </div>
      </Card>
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

function documentLabel(documentType: string) {
  const labels: Record<string, string> = {
    identity: "Kimlik Belgesi",
    income: "Gelir Belgesi",
    payroll: "Gelir Belgesi",
    bank: "Banka Hesap Dökümü",
    bank_statement: "Banka Hesap Dökümü",
  };
  return labels[documentType] || "Başvuru Belgesi";
}

function defaultCreditOfferForm(application: ApplicationRecord): CreditOfferForm {
  const amount = parseMoneyValue(application.credit_request?.requested_amount);
  const term = parseMoneyValue(application.credit_request?.term_months);
  return {
    approvedAmount: Number.isFinite(amount) && amount > 0 ? String(Math.round(amount)) : "",
    termMonths: Number.isFinite(term) && term > 0 ? String(Math.round(term)) : "36",
    monthlyInterestRate: (suggestedMonthlyInterestRate(application) * 100).toFixed(2),
  };
}

function creditOfferPayload(creditOffer: CreditOfferForm): CreditOfferInput {
  const approvedAmount = parseMoneyValue(creditOffer.approvedAmount);
  const termMonths = parseMoneyValue(creditOffer.termMonths);
  const monthlyInterestPercent = parseMoneyValue(creditOffer.monthlyInterestRate);

  return {
    approved_amount: Number.isFinite(approvedAmount) && approvedAmount > 0 ? approvedAmount : undefined,
    term_months: Number.isFinite(termMonths) && termMonths > 0 ? Math.round(termMonths) : undefined,
    monthly_interest_rate: Number.isFinite(monthlyInterestPercent) && monthlyInterestPercent > 0
      ? Number((monthlyInterestPercent / 100).toFixed(4))
      : undefined,
  };
}

function shouldAllowCreditOffer(application: ApplicationRecord) {
  const riskScore = Number(application.risk_score || 0);
  return application.risk_level === "Orta" || application.risk_level === "Yüksek" || riskScore >= 34;
}

function suggestedMonthlyInterestRate(application: ApplicationRecord) {
  const raw = application.raw && typeof application.raw === "object" ? application.raw as any : {};
  const policyRate = raw?.payment_plan?.interest_policy?.assigned_monthly_interest_rate;
  if (Number.isFinite(Number(policyRate)) && Number(policyRate) > 0) {
    return Number(policyRate);
  }

  const requestedAmount = parseMoneyValue(application.credit_request?.requested_amount);
  const termMonths = parseMoneyValue(application.credit_request?.term_months);
  const riskScore = Number(application.risk_score || 0);
  const normalizedScore = riskScore > 1 ? riskScore / 100 : riskScore;
  const riskAdjustment = application.risk_level === "Yüksek" || normalizedScore >= 0.67
    ? 0.011
    : application.risk_level === "Orta" || normalizedScore >= 0.34
      ? 0.0055
      : 0;
  const amountAdjustment = requestedAmount >= 500000 ? 0.003 : requestedAmount >= 250000 ? 0.0015 : 0;
  const termAdjustment = termMonths >= 48 ? 0.004 : termMonths >= 36 ? 0.002 : 0;
  return Math.min(0.0425, Math.max(0.0185, 0.025 + riskAdjustment + amountAdjustment + termAdjustment));
}

function buildRiskReviewDetails(selected: ApplicationRecord) {
  const riskScore = Number(selected.risk_score || 0);
  const riskLevel = String(selected.risk_level || "").trim();
  const mediumOrHighRisk = riskLevel === "Orta" || riskLevel === "Yüksek" || riskScore >= 34;
  const highRisk = riskLevel === "Yüksek" || riskScore >= 67;
  const tone: "gold" | "red" = highRisk ? "red" : "gold";
  const raw = selected.raw && typeof selected.raw === "object" ? selected.raw as any : {};
  const riskSummary = raw?.risk_summary || {};
  const bankView = raw?.bank_view || {};
  const risk = raw?.risk || {};
  const consistency = raw?.consistency || {};
  const formDocumentConsistency = raw?.form_document_consistency || {};
  const monthlyIncome = parseMoneyValue(selected.credit_request?.declared_monthly_income);
  const requestedAmount = parseMoneyValue(selected.credit_request?.requested_amount);
  const currentDebt = parseMoneyValue(selected.credit_request?.current_total_debt);
  const totalDebtPressure = requestedAmount + currentDebt;
  const debtIncomeRatio = monthlyIncome > 0 && totalDebtPressure > 0 ? totalDebtPressure / monthlyIncome : Number.NaN;

  const riskSignals = uniqueStrings([
    ...(selected.reasons || []),
    ...(riskSummary.main_reasons || []),
    ...(risk.reasons || []),
    ...(risk.decision_summary?.main_reasons || []),
    ...(bankView.main_reasons || []),
    selected.ai_recommendation || "",
    selected.system_action || "",
    riskScore ? `Risk skoru %${riskScore}; başvuru ${highRisk ? "yüksek" : "orta"} risk bandında.` : "",
    Number.isFinite(debtIncomeRatio) && debtIncomeRatio >= 6
      ? `Talep edilen kredi ve mevcut borç toplamı aylık gelirin yaklaşık ${debtIncomeRatio.toFixed(1)} katı.`
      : "",
  ]);

  const documentFindings = uniqueStrings([
    ...(riskSummary.consistency_flags || []),
    ...(riskSummary.form_document_flags || []),
    ...(riskSummary.data_precedence_warnings || []),
    ...(riskSummary.blockers || []),
    ...(bankView.form_document_flags || []),
    ...(bankView.blockers || []),
    ...(formDocumentConsistency.flags || []),
    ...(consistency.flags || []),
    ...(raw?.data_precedence_warnings || []),
    selected.consistency_score !== undefined && selected.consistency_score < 0.85
      ? `Tutarlılık skoru ${scorePercent(selected.consistency_score)}; kimlik, gelir ve banka bilgileri birlikte kontrol edilmeli.`
      : "",
    selected.anomaly_score !== undefined && selected.anomaly_score > 0
      ? `Anomali skoru ${scorePercent(selected.anomaly_score)}; banka hareketlerinde olağandışı çıkış veya borç hareketi aranmalı.`
      : "",
    selected.document_confidence_score !== undefined && selected.document_confidence_score < 0.9
      ? `Belge güven skoru ${scorePercent(selected.document_confidence_score)}; okunamayan veya eksik alanlar tekrar incelenmeli.`
      : "",
  ]);

  const reviewFocus = highRisk
    ? [
        "Son 6 aylık banka dökümünde düzenli maaş girişi, kredi/kart borcu ve olağandışı nakit çıkışlarını kontrol et.",
        "Güncel gelir belgesi ile banka maaş girişlerini tutar ve işveren bazında karşılaştır.",
        "Ek belge isteme, detaylı inceleme veya ret kararını kanaat raporunda açık gerekçeyle yaz.",
      ]
    : [
        "Gelir düzenliliğini, harcama/gelir dengesini ve mevcut borç yükünü birlikte değerlendir.",
        "Belge sinyalleri net değilse güncel gelir belgesi veya son 6 aylık hesap dökümü iste.",
        "Onay veya ek belge kararını verirken bu gerekçeleri uzman kanaat raporuna geçir.",
      ];

  return {
    shouldShow: mediumOrHighRisk,
    tone,
    badge: highRisk ? "Yüksek risk" : "Orta risk",
    summary: highRisk
      ? "Bu başvuru detaylı manuel inceleme gerektiriyor. Karardan önce belge tutarlılığı, borç yükü ve banka hareketlerindeki anomali sinyalleri birlikte değerlendirilmelidir."
      : "Bu başvuru orta riskte. Otomatik onay yerine uzman yorumu gerekir; karar gelir, borç ve belge tutarlılığına göre netleştirilmelidir.",
    riskSignals: riskSignals.length ? riskSignals.slice(0, 6) : ["Risk seviyesi uzman incelemesi gerektirecek bandda hesaplandı."],
    documentFindings: documentFindings.length ? documentFindings.slice(0, 6) : ["Belge skorlarında karar öncesi manuel kontrol gerektiren sinyaller bulunuyor."],
    reviewFocus,
  };
}

function uniqueStrings(values: string[]) {
  return Array.from(new Set(values.map((item) => String(item || "").trim()).filter(Boolean)));
}

function WorkflowLine({ title, text, tone }: { title: string; text: string; tone: "gold" | "green" | "red" }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/25 p-4">
      <StatusBadge tone={tone}>{title}</StatusBadge>
      <p className="mt-3">{text}</p>
    </div>
  );
}

function isAutoPreApproved(application: ApplicationRecord) {
  return application.review_route === "auto_pre_approved" || application.status_code === "PRE_APPROVED" || application.risk_level === "Düşük";
}

function isManualReview(application: ApplicationRecord) {
  if (isDecisionFinal(application)) {
    return false;
  }
  return !isAutoPreApproved(application);
}

function isDecisionFinal(application: ApplicationRecord) {
  const raw = application.raw as any;
  const statusCode = String(application.status_code || raw?.current_status?.status_code || "").toUpperCase();
  return (
    application.review_route === "completed"
    || statusCode === "APPROVED"
    || statusCode === "REJECTED"
  );
}

function riskTone(application: ApplicationRecord): "gold" | "green" | "red" | "neutral" {
  if (application.risk_level === "Yüksek") return "red";
  if (application.risk_level === "Düşük") return "green";
  return "gold";
}

function routeTone(application: ApplicationRecord): "gold" | "green" | "red" | "neutral" {
  if (application.review_route === "auto_pre_approved") return "green";
  if (application.review_route === "deep_review") return "red";
  if (application.review_route === "completed") return "neutral";
  return "gold";
}

function parseRequestedDocuments(value: string) {
  const items = value
    .split(/[,;\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
  return items.length ? items : ["Güncel gelir belgesi"];
}

function replaceApplication(items: ApplicationRecord[], updated: ApplicationRecord) {
  const exists = items.some((item) => item.application_id === updated.application_id);
  if (!exists) {
    return [updated, ...items];
  }
  return items.map((item) => (item.application_id === updated.application_id ? updated : item));
}

function defaultDecisionNote(action: ExpertDecision, selected: ApplicationRecord) {
  if (action === "approve") return `${selected.customer_name} başvurusu uzman tarafından onaylandı.`;
  if (action === "revise") return `${selected.customer_name} başvurusu için revizyon talep edildi.`;
  if (action === "extra") return `${selected.customer_name} başvurusu için ek belge talep edildi.`;
  return `${selected.customer_name} başvurusu banka politikası gereği reddedildi.`;
}

function decisionToast(action: ExpertDecision) {
  if (action === "approve") return "Başvuru onaylandı ve backend kaydı güncellendi.";
  if (action === "revise") return "Revizyon kararı başvuru kaydına işlendi.";
  if (action === "extra") return "Ek belge talebi müşterinin başvuru ekranına düşecek şekilde kaydedildi.";
  return "Ret kararı başvuru kaydına işlendi.";
}

function formatCreditValue(value: unknown) {
  const numeric = parseMoneyValue(value);
  if (Number.isFinite(numeric) && numeric > 0) {
    return formatCurrency(numeric);
  }
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  return "Belirtilmedi";
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

function formatDate(value: string) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("tr-TR");
}
