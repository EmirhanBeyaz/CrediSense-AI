"use client";

import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { demoApplications } from "@/lib/demoData";
import { formatCurrency, scorePercent } from "@/lib/format";
import {
  approveApplication,
  createExpertReport,
  getExpertApplications,
  rejectApplication,
  requestExtraDocument,
  reviseApplication,
} from "@/services/expertService";
import { getReports } from "@/services/reportService";
import type { ApplicationRecord, ExpertView, ReportSummary } from "@/types";

type ExpertViewsProps = {
  activeView: ExpertView;
  showToast: (message: string) => void;
};

type ExpertDecision = "approve" | "revise" | "extra" | "reject";

export function ExpertViews({ activeView, showToast }: ExpertViewsProps) {
  const [applications, setApplications] = useState<ApplicationRecord[]>(demoApplications);
  const [selectedId, setSelectedId] = useState(demoApplications[0].application_id);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [decisionNote, setDecisionNote] = useState("");
  const [extraDocumentText, setExtraDocumentText] = useState("Güncel gelir belgesi");
  const [reportText, setReportText] = useState("");

  useEffect(() => {
    refreshExpertData();
  }, [activeView]);

  const selected = useMemo(
    () => applications.find((application) => application.application_id === selectedId) || applications[0] || demoApplications[0],
    [applications, selectedId],
  );
  const manualApplications = useMemo(() => applications.filter(isManualReview), [applications]);

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

      if (action === "approve") updated = await approveApplication(selected.application_id, note);
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
        onDecision={handleDecision}
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
    return <DocumentControl selected={selected} />;
  }
  if (activeView === "risk-analysis") {
    return <RiskAnalysis selected={selected} />;
  }
  if (activeView === "decision-process") {
    return (
      <DecisionProcess
        decisionNote={decisionNote}
        extraDocumentText={extraDocumentText}
        loading={actionLoading}
        onDecision={handleDecision}
        onDecisionNoteChange={setDecisionNote}
        onExtraDocumentTextChange={setExtraDocumentText}
        selected={selected}
      />
    );
  }
  if (activeView === "reports") {
    return <ReportsView reports={reports} />;
  }
  return <ProfileView />;
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
  reportText,
  onSelect,
  onDecision,
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
  reportText: string;
  onSelect: (id: string) => void;
  onDecision: (decision: ExpertDecision) => void;
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
          loading={actionLoading}
          onDecision={onDecision}
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

function DocumentControl({ selected }: { selected: ApplicationRecord }) {
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
      <Card className="xl:col-span-3">
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Belge Kontrolü</p>
        <h2 className="mt-2 font-display text-3xl font-bold">{selected.customer_name}</h2>
        <div className="mt-6 grid gap-3 md:grid-cols-3">
          {["Kimlik belgesi doğrulandı", "Gelir belgesi okunabilir", "Banka dökümü analiz edildi"].map((text) => (
            <div className="rounded-xl border border-secondary/20 bg-secondary/10 p-4 text-sm text-muted" key={text}>
              <span className="material-symbols-outlined mb-3 text-secondary">task_alt</span>
              <strong className="block text-white">{text}</strong>
            </div>
          ))}
        </div>
      </Card>
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
  onDecision,
  onDecisionNoteChange,
  onExtraDocumentTextChange,
}: {
  selected: ApplicationRecord;
  loading: boolean;
  decisionNote: string;
  extraDocumentText: string;
  onDecision: (decision: ExpertDecision) => void;
  onDecisionNoteChange: (value: string) => void;
  onExtraDocumentTextChange: (value: string) => void;
}) {
  return (
    <Card>
      <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Karar Süreci</p>
      <h2 className="mt-2 font-display text-3xl font-bold">{selected.customer_name}</h2>
      <p className="mt-3 max-w-3xl text-muted">
        Bu ekrandaki aksiyonlar doğrudan backend başvuru kaydına işlenir. Ek belge istenirse müşteri hesabında ilgili başvuru için yükleme aksiyonu açılır.
      </p>
      <DecisionControls
        decisionNote={decisionNote}
        extraDocumentText={extraDocumentText}
        loading={loading}
        onDecision={onDecision}
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
  onDecision,
  onDecisionNoteChange,
  onExtraDocumentTextChange,
}: {
  selected: ApplicationRecord;
  loading: boolean;
  decisionNote: string;
  extraDocumentText: string;
  onDecision: (decision: ExpertDecision) => void;
  onDecisionNoteChange: (value: string) => void;
  onExtraDocumentTextChange: (value: string) => void;
}) {
  const finalStatus = isDecisionFinal(selected);

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
      <label className="grid gap-2 text-sm text-muted">
        Ek belge adları
        <input
          className="rounded-lg border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-primary/60"
          onChange={(event) => onExtraDocumentTextChange(event.target.value)}
          placeholder="Güncel gelir belgesi, ek banka dökümü"
          value={extraDocumentText}
        />
      </label>
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

function ReportsView({ reports }: { reports: ReportSummary[] }) {
  return (
    <Card>
      <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Raporlar</p>
      <h2 className="mt-2 font-display text-3xl font-bold">Uzman rapor ekranı</h2>
      {!reports.length ? (
        <div className="mt-6">
          <EmptyState title="Henüz rapor yok" description="Başvuru detayında yazılan kanaat raporları ve analiz raporları burada listelenir." />
        </div>
      ) : (
        <div className="mt-6 grid gap-3">
          {reports.map((report) => (
            <article className="rounded-xl border border-white/10 bg-black/25 p-4" key={report.id}>
              <div className="grid gap-3 md:grid-cols-[1fr_auto_auto] md:items-center">
                <strong>{report.title}</strong>
                <span className="text-sm text-muted">{formatDate(report.createdAt)}</span>
                <StatusBadge tone="gold">{report.type}</StatusBadge>
              </div>
              {report.applicationId ? <p className="mt-2 text-sm text-muted">Başvuru: {report.applicationId}</p> : null}
              {report.content ? <p className="mt-3 rounded-lg border border-white/10 bg-white/[0.03] p-3 text-sm text-muted">{report.content}</p> : null}
            </article>
          ))}
        </div>
      )}
    </Card>
  );
}

function ProfileView() {
  return (
    <Card>
      <EmptyState title="Uzman profili hazır" description="Kurumsal kullanıcı yetkileri ve güvenlik ayarları auth servisi üzerinden yönetilecek." />
    </Card>
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
    || raw?.current_status?.is_final === true
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
