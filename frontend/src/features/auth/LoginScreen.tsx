"use client";

import type { Role } from "@/types";
import { useState } from "react";

type RegisterForm = {
  role: Role;
  username: string;
  email: string;
  password: string;
  full_name: string;
  title?: string;
};

type RegisterResult = {
  message: string;
  developmentToken?: string;
};

type LoginScreenProps = {
  onLogin: (role: Role, identifier: string, password: string) => void;
  onRegister: (form: RegisterForm) => Promise<RegisterResult>;
  onVerifyEmail: (identifier: string, token: string) => void;
  loading: boolean;
};

export function LoginScreen({ onLogin, onRegister, onVerifyEmail, loading }: LoginScreenProps) {
  return (
    <main className="relative min-h-screen overflow-hidden px-6 py-10">
      <div className="ambient-grid fixed inset-0 -z-10" />
      <section className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl content-center gap-10">
        <div className="max-w-4xl">
          <div className="gold-gradient mb-6 grid h-16 w-16 place-items-center rounded-2xl text-xl font-black text-black">CS</div>
          <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-[0.18em] text-primary">CrediSense AI</p>
          <h1 className="font-display text-5xl font-bold leading-tight md:text-7xl">
            Akilli kredi risk ve belge analiz sistemi
          </h1>
          <p className="mt-5 max-w-3xl text-lg leading-8 text-muted">
            Musteri basvurusu, belge analizi, banka uzman incelemesi ve odeme sonrasi destek icin iki ayri rol tabanli arayuz.
          </p>
        </div>

        <div className="grid gap-5 lg:grid-cols-2">
          <AuthCard
            buttonLabel="Musteri olarak giris yap"
            defaultIdentifier="musteri@gmail.com"
            description="Yeni basvuru olustur, PDF belgelerini yukle, AI analiz surecini takip et ve odeme planini yonet."
            icon="person"
            loading={loading}
            onLogin={(identifier, password) => onLogin("customer", identifier, password)}
            onRegister={onRegister}
            onVerifyEmail={onVerifyEmail}
            role="customer"
            title="Musteri Girisi"
          />
          <AuthCard
            buttonLabel="Uzman paneline giris yap"
            defaultIdentifier="uzman@gmail.com"
            description="Basvuru kuyrugunu incele, belge guven skorlarini degerlendir ve nihai banka kararini isle."
            icon="account_balance"
            loading={loading}
            onLogin={(identifier, password) => onLogin("expert", identifier, password)}
            onRegister={onRegister}
            onVerifyEmail={onVerifyEmail}
            role="expert"
            title="Banka Uzmani Girisi"
          />
        </div>
      </section>
    </main>
  );
}

type AuthCardProps = {
  icon: string;
  title: string;
  description: string;
  buttonLabel: string;
  defaultIdentifier: string;
  role: Role;
  onLogin: (identifier: string, password: string) => void;
  onRegister: (form: RegisterForm) => Promise<RegisterResult>;
  onVerifyEmail: (identifier: string, token: string) => void;
  loading: boolean;
};

function AuthCard({
  icon,
  title,
  description,
  buttonLabel,
  defaultIdentifier,
  role,
  onLogin,
  onRegister,
  onVerifyEmail,
  loading,
}: AuthCardProps) {
  const [mode, setMode] = useState<"login" | "register" | "verify">("login");
  const [identifier, setIdentifier] = useState(defaultIdentifier);
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [verificationIdentifier, setVerificationIdentifier] = useState(defaultIdentifier);
  const [verificationToken, setVerificationToken] = useState("");
  const [developmentToken, setDevelopmentToken] = useState("");
  const [message, setMessage] = useState("");

  async function handleRegister() {
    try {
      const result = await onRegister({
        role,
        username,
        email,
        password,
        full_name: fullName,
        title: role === "expert" ? "Banka uzmani" : "Musteri",
      });
      setVerificationIdentifier(email || username);
      setDevelopmentToken(result.developmentToken || "");
      setMessage(result.message);
      setMode("verify");
    } catch {
      setMessage("Kayit olusturulamadi. Bilgileri kontrol edin.");
    }
  }

  return (
    <article className="glass-panel rounded-2xl p-7 transition hover:-translate-y-1 hover:border-primary/40 hover:shadow-glow">
      <span className="material-symbols-outlined gold-gradient mb-7 grid h-12 w-12 place-items-center rounded-xl text-black">
        {icon}
      </span>
      <h2 className="font-display text-2xl font-bold">{title}</h2>
      <p className="mt-3 min-h-16 text-sm leading-6 text-muted">{description}</p>

      <div className="mt-6 grid grid-cols-3 gap-2 rounded-xl border border-white/10 bg-black/20 p-1">
        <button className={tabClass(mode === "login")} onClick={() => setMode("login")} type="button">Giris</button>
        <button className={tabClass(mode === "register")} onClick={() => setMode("register")} type="button">Kayit</button>
        <button className={tabClass(mode === "verify")} onClick={() => setMode("verify")} type="button">Dogrula</button>
      </div>

      {mode === "login" ? (
        <div className="mt-6 grid gap-3">
          <TextField label="Kullanici veya e-posta" onChange={setIdentifier} value={identifier} />
          <TextField label="Sifre" onChange={setPassword} placeholder="Sifrenizi girin" type="password" value={password} />
          <button
            className="gold-gradient mt-2 rounded-lg px-5 py-3 font-bold text-black transition hover:shadow-glow disabled:opacity-70"
            disabled={loading}
            onClick={() => onLogin(identifier, password)}
            type="button"
          >
            {loading ? "Giris yapiliyor" : buttonLabel}
          </button>
        </div>
      ) : null}

      {mode === "register" ? (
        <div className="mt-6 grid gap-3">
          <TextField label="Ad soyad" onChange={setFullName} value={fullName} />
          <TextField label="Kullanici adi" onChange={setUsername} value={username} />
          <TextField label="E-posta" onChange={setEmail} type="email" value={email} />
          <TextField label="Sifre" onChange={setPassword} placeholder="En az 6 karakter" type="password" value={password} />
          <button
            className="gold-gradient mt-2 rounded-lg px-5 py-3 font-bold text-black transition hover:shadow-glow disabled:opacity-70"
            disabled={loading}
            onClick={handleRegister}
            type="button"
          >
            {loading ? "Kayit olusturuluyor" : "Kayit ol ve e-postayi dogrula"}
          </button>
        </div>
      ) : null}

      {mode === "verify" ? (
        <div className="mt-6 grid gap-3">
          <TextField label="Kullanici veya e-posta" onChange={setVerificationIdentifier} value={verificationIdentifier} />
          <TextField label="Dogrulama tokeni" onChange={setVerificationToken} value={verificationToken} />
          {message ? <p className="rounded-lg border border-white/10 bg-white/[0.03] p-3 text-xs text-muted">{message}</p> : null}
          {developmentToken ? (
            <p className="rounded-lg border border-primary/30 bg-primary/10 p-3 text-xs text-primary">
              Yerel gelistirme tokeni: {developmentToken}
            </p>
          ) : null}
          <button
            className="gold-gradient mt-2 rounded-lg px-5 py-3 font-bold text-black transition hover:shadow-glow disabled:opacity-70"
            disabled={loading}
            onClick={() => onVerifyEmail(verificationIdentifier, verificationToken)}
            type="button"
          >
            {loading ? "Dogrulaniyor" : "E-postayi dogrula ve giris yap"}
          </button>
        </div>
      ) : null}
    </article>
  );
}

function TextField({
  label,
  onChange,
  placeholder = "",
  type = "text",
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
  value: string;
}) {
  return (
    <label className="grid gap-2 text-sm text-muted">
      {label}
      <input
        className="rounded-lg border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-primary/60"
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        type={type}
        value={value}
      />
    </label>
  );
}

function tabClass(active: boolean) {
  return `rounded-lg px-3 py-2 text-sm font-semibold transition ${
    active ? "bg-primary text-black" : "text-muted hover:bg-white/5 hover:text-white"
  }`;
}
