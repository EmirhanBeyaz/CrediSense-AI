"use client";

import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { demoApplications } from "@/lib/demoData";
import { scorePercent } from "@/lib/format";
import {
  approveApplication,
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

export function ExpertViews({ activeView, showToast }: ExpertViewsProps) {
  const [applications, setApplications] = useState<ApplicationRecord[]>(demoApplications);
  const [selectedId, setSelectedId] = useState(demoApplications[0].application_id);
  const [loading, setLoading] = useState(false);
  const [reports, setReports] = useState<ReportSummary[]>([]);

  useEffect(() => {
    setLoading(true);
    getExpertApplications()
      .then((items) => {
        setApplications(items.length ? items : demoApplications);
        setSelectedId((items[0] || demoApplications[0]).application_id);
      })
      .catch(() => setApplications(demoApplications))
      .finally(() => setLoading(false));

    getReports().then(setReports);
  }, []);

  const selected = useMemo(
    () => applications.find((application) => application.application_id === selectedId) || applications[0] || demoApplications[0],
    [applications, selectedId],
  );

  async function handleDecision(action: "approve" | "revise" | "extra" | "reject") {
    setLoading(true);
    try {
      if (action === "approve") await approveApplication(selected.application_id, "Uzman tarafından onaylandı.");
      if (action === "revise") await reviseApplication(selected.application_id, "Detaylı incelemeye alındı.");
      if (action === "extra") await requestExtraDocument(selected.application_id, ["Güncel gelir belgesi"], "Ek belge istendi.");
      if (action === "reject") await rejectApplication(selected.application_id, "Banka politikası gereği reddedildi.");
      showToast("Uzman karar akışı tamamlandı.");
      const refreshed = await getExpertApplications();
      setApplications(refreshed.length ? refreshed : applications);
    } catch {
      showToast("Backend yanıtı alınamadı, karar demo akışta işlendi.");
    } finally {
      setLoading(false);
    }
  }

  if (loading && applications.length === 0) {
    return <LoadingState label="Başvurular yükleniyor" />;
  }

  if (activeView === "expert-home") {
    return <ExpertHome applications={applications} />;
  }
  if (activeView === "application-queue" || activeView === "pending-review") {
    return <ApplicationQueue applications={applications} selectedId={selectedId} onSelect={setSelectedId} />;
  }
  if (activeView === "document-control") {
    return <DocumentControl selected={selected} />;
  }
  if (activeView === "risk-analysis") {
    return <RiskAnalysis selected={selected} />;
  }
  if (activeView === "decision-process") {
    return <DecisionProcess loading={loading} selected={selected} onDecision={handleDecision} />;
  }
  if (activeView === "reports") {
    return <ReportsView reports={reports} />;
  }
  return <ProfileView />;
}

function ExpertHome({ applications }: { applications: ApplicationRecord[] }) {
  const highRiskCount = applications.filter((item) => item.risk_level === "Yüksek").length;
  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_420px]">
      <Card>
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Uzman Paneli</p>
        <h2 className="mt-2 font-display text-4xl font-bold">Banka uzman çalışma alanı</h2>
        <p className="mt-4 max-w-2xl text-muted">
          AI skorları öneri ve açıklama sağlar. Nihai değerlendirme banka uzmanı kararıyla tamamlanır.
        </p>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          <MetricCard label="Toplam Başvuru" value={applications.length} />
          <MetricCard label="Yüksek Risk" value={highRiskCount} tone="red" />
          <MetricCard label="Manuel İnceleme" value={applications.filter((item) => item.status.includes("inceleme")).length} tone="green" />
        </div>
      </Card>
      <Card>
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">AI Öneri Notu</p>
        <p className="mt-4 text-muted">
          Risk skoru, belge güven skoru, tutarlılık skoru ve anomali skoru birlikte değerlendirilmelidir. AI hiçbir ekranda nihai karar veren taraf değildir.
        </p>
      </Card>
    </div>
  );
}

function ApplicationQueue({
  applications,
  selectedId,
  onSelect,
}: {
  applications: ApplicationRecord[];
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  if (!applications.length) {
    return <EmptyState title="Başvuru yok" description="Backend başvuru deposunda kayıt bulunamadı." />;
  }

  return (
    <Card>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Başvuru Kuyruğu</p>
          <h2 className="mt-2 font-display text-3xl font-bold">İnceleme bekleyen başvurular</h2>
        </div>
        <StatusBadge tone="gold">Backend /applications</StatusBadge>
      </div>
      <div className="grid gap-3">
        {applications.map((application) => (
          <button
            className={`grid grid-cols-[1fr_auto_auto] items-center gap-3 rounded-xl border p-4 text-left transition ${
              selectedId === application.application_id ? "border-primary/50 bg-primary/10" : "border-white/10 bg-black/25 hover:border-primary/30"
            }`}
            key={application.application_id}
            onClick={() => onSelect(application.application_id)}
            type="button"
          >
            <div>
              <strong>{application.customer_name}</strong>
              <span className="mt-1 block text-sm text-muted">{application.application_id}</span>
            </div>
            <span className="text-muted">{application.status}</span>
            <StatusBadge tone={application.risk_level === "Yüksek" ? "red" : application.risk_level === "Düşük" ? "green" : "gold"}>
              {application.risk_level || "Orta"}
            </StatusBadge>
          </button>
        ))}
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
          <strong className="font-display text-5xl text-primary">{selected.risk_score || 72}</strong>
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
      </Card>
    </div>
  );
}

function DecisionProcess({
  selected,
  loading,
  onDecision,
}: {
  selected: ApplicationRecord;
  loading: boolean;
  onDecision: (decision: "approve" | "revise" | "extra" | "reject") => void;
}) {
  return (
    <Card>
      <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Karar Süreci</p>
      <h2 className="mt-2 font-display text-3xl font-bold">{selected.customer_name}</h2>
      <p className="mt-3 max-w-3xl text-muted">
        AI önerisi sadece destek amaçlıdır. Nihai karar banka uzmanı tarafından bu ekrandaki aksiyonlarla backend’e işlenir.
      </p>
      <div className="mt-7 grid gap-4 md:grid-cols-4">
        <button className="gold-gradient rounded-lg px-5 py-4 font-bold text-black disabled:opacity-60" disabled={loading} onClick={() => onDecision("approve")} type="button">
          Onayla
        </button>
        <button className="rounded-lg border border-white/10 bg-white/[0.04] px-5 py-4 font-bold disabled:opacity-60" disabled={loading} onClick={() => onDecision("revise")} type="button">
          Revize Et
        </button>
        <button className="rounded-lg border border-primary/30 bg-primary/10 px-5 py-4 font-bold text-primary disabled:opacity-60" disabled={loading} onClick={() => onDecision("extra")} type="button">
          Ek Belge İste
        </button>
        <button className="rounded-lg border border-danger/30 bg-danger/10 px-5 py-4 font-bold text-danger disabled:opacity-60" disabled={loading} onClick={() => onDecision("reject")} type="button">
          Reddet
        </button>
      </div>
      {loading ? <div className="mt-5"><LoadingState label="Karar backend servisine gönderiliyor" /></div> : null}
    </Card>
  );
}

function ReportsView({ reports }: { reports: ReportSummary[] }) {
  return (
    <Card>
      <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Raporlar</p>
      <h2 className="mt-2 font-display text-3xl font-bold">Uzman rapor ekranı</h2>
      <div className="mt-6 grid gap-3">
        {reports.map((report) => (
          <div className="grid grid-cols-[1fr_auto_auto] items-center gap-3 rounded-xl border border-white/10 bg-black/25 p-4" key={report.id}>
            <strong>{report.title}</strong>
            <span className="text-sm text-muted">{report.createdAt}</span>
            <StatusBadge tone="gold">{report.type}</StatusBadge>
          </div>
        ))}
      </div>
    </Card>
  );
}

function ProfileView() {
  return (
    <Card>
      <EmptyState title="Uzman profili hazır" description="Kurumsal kullanıcı yetkileri ve güvenlik ayarları auth servisi tamamlandığında burada gösterilecek." />
    </Card>
  );
}
