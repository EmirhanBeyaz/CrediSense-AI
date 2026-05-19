import type { AppView, Role, User } from "@/types";

type MenuItem = {
  id: AppView;
  label: string;
  icon: string;
};

const customerMenu: MenuItem[] = [
  { id: "customer-home", label: "Ana Panel", icon: "dashboard" },
  { id: "new-application", label: "Yeni Başvuru", icon: "edit_note" },
  { id: "documents", label: "Belgelerim", icon: "folder" },
  { id: "analysis-process", label: "AI Analiz Süreci", icon: "neurology" },
  { id: "analysis-results", label: "Analiz Sonuçlarım", icon: "analytics" },
  { id: "bank-approval", label: "Banka Onayı", icon: "approval_delegation" },
  { id: "payment-plan", label: "Ödeme Planım", icon: "calendar_month" },
  { id: "assistant", label: "AI Finans Asistanı", icon: "support_agent" },
  { id: "customer-profile", label: "Profil", icon: "person" },
];

const expertMenu: MenuItem[] = [
  { id: "expert-home", label: "Uzman Paneli", icon: "space_dashboard" },
  { id: "application-queue", label: "Başvuru Kuyruğu", icon: "list_alt" },
  { id: "pending-review", label: "İnceleme Bekleyenler", icon: "hourglass_top" },
  { id: "document-control", label: "Belge Kontrolü", icon: "fact_check" },
  { id: "risk-analysis", label: "Risk Analizi", icon: "monitoring" },
  { id: "decision-process", label: "Karar Süreci", icon: "gavel" },
  { id: "reports", label: "Raporlar", icon: "summarize" },
  { id: "expert-profile", label: "Profil", icon: "person" },
];

type SidebarProps = {
  role: Role;
  user: User;
  activeView: AppView;
  onNavigate: (view: AppView) => void;
  onLogout: () => void;
};

export function Sidebar({ role, user, activeView, onNavigate, onLogout }: SidebarProps) {
  const menu = role === "customer" ? customerMenu : expertMenu;

  return (
    <aside className="sticky top-0 flex h-screen w-[286px] shrink-0 flex-col border-r border-white/10 bg-black/40 p-5 backdrop-blur-xl">
      <div className="mb-8 flex items-center gap-3">
        <div className="gold-gradient grid h-12 w-12 place-items-center rounded-xl font-bold text-black">CS</div>
        <div>
          <strong className="block font-display text-lg">CrediSense AI</strong>
          <span className="text-sm text-muted">{role === "customer" ? "Müşteri portalı" : "Uzman portalı"}</span>
        </div>
      </div>

      <div className="mb-7 rounded-xl border border-white/10 bg-white/[0.04] p-4">
        <div className="flex items-center gap-3">
          <div className="gold-gradient grid h-11 w-11 place-items-center rounded-lg font-bold text-black">
            {user.fullName.split(" ").map((part) => part[0]).join("").slice(0, 2)}
          </div>
          <div>
            <strong className="block">{user.fullName}</strong>
            <span className="text-sm text-muted">{user.title}</span>
          </div>
        </div>
      </div>

      <nav className="grid gap-2">
        {menu.map((item) => (
          <button
            className={`flex items-center gap-3 rounded-lg border px-4 py-3 text-left transition ${
              activeView === item.id
                ? "border-primary/40 bg-primary/10 text-primary shadow-glow"
                : "border-transparent text-muted hover:border-white/10 hover:bg-white/[0.04] hover:text-white"
            }`}
            key={item.id}
            onClick={() => onNavigate(item.id)}
            type="button"
          >
            <span className="material-symbols-outlined">{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="mt-auto grid gap-2">
        <button
          className={`flex items-center gap-3 rounded-lg border px-4 py-3 text-left transition ${
            activeView === (role === "customer" ? "customer-settings" : "expert-settings")
              ? "border-primary/40 bg-primary/10 text-primary shadow-glow"
              : "border-transparent text-muted hover:border-white/10 hover:bg-white/[0.04] hover:text-white"
          }`}
          onClick={() => onNavigate(role === "customer" ? "customer-settings" : "expert-settings")}
          type="button"
        >
          <span className="material-symbols-outlined">settings</span>
          Ayarlar
        </button>
        <button className="flex items-center gap-3 rounded-lg px-4 py-3 text-left text-muted hover:bg-white/[0.04]" onClick={onLogout} type="button">
          <span className="material-symbols-outlined">logout</span>
          Çıkış
        </button>
      </div>
    </aside>
  );
}
