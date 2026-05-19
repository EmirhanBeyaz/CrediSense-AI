import type { ReactNode } from "react";
import type { AppView, Role, User } from "@/types";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

type AppShellProps = {
  role: Role;
  user: User;
  activeView: AppView;
  title: string;
  subtitle: string;
  children: ReactNode;
  onNavigate: (view: AppView) => void;
  onLogout: () => void;
};

export function AppShell({ role, user, activeView, title, subtitle, children, onNavigate, onLogout }: AppShellProps) {
  return (
    <div className="min-h-screen">
      <div className="ambient-grid fixed inset-0 -z-10" />
      <div className="flex min-h-screen">
        <Sidebar role={role} user={user} activeView={activeView} onNavigate={onNavigate} onLogout={onLogout} />
        <main className="min-w-0 flex-1 px-8 py-8">
          <Topbar title={title} subtitle={subtitle} />
          <div className="page-enter">{children}</div>
        </main>
      </div>
    </div>
  );
}
