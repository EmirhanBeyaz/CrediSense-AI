import { apiRequest, clearAuthToken, setAuthToken } from "@/lib/apiClient";
import { endpoints } from "@/lib/endpoints";
import type { Role, User } from "@/types";

type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: ApiUser;
};

export type RegisterPayload = {
  role: Role;
  username: string;
  email: string;
  password: string;
  full_name: string;
  title?: string;
  profile?: Record<string, unknown>;
};

export type RegisterResponse = {
  user: ApiUser;
  verification_required: boolean;
  email_sent: boolean;
  email_provider: string;
  expires_at: string;
  message: string;
  development_token?: string;
};

type ApiUser = {
  id: string;
  username?: string;
  email?: string;
  role: Role;
  full_name: string;
  title: string;
  email_verified?: boolean;
  profile?: User["profile"];
};

export async function login(role: Role, identifier: string, password: string): Promise<User> {
  const response = await apiRequest<LoginResponse>(endpoints.login, {
    method: "POST",
    body: {
      identifier,
      password,
      role,
    },
  });

  if (!response.data) {
    throw new Error(response.error || "Giris yapilamadi.");
  }

  setAuthToken(response.data.access_token);
  return mapUser(response.data.user);
}

export async function register(payload: RegisterPayload): Promise<RegisterResponse> {
  const response = await apiRequest<RegisterResponse>(endpoints.register, {
    method: "POST",
    body: payload,
  });

  if (!response.data) {
    throw new Error(response.error || "Kayit olusturulamadi.");
  }

  return response.data;
}

export async function verifyEmail(identifier: string, token: string): Promise<User> {
  const response = await apiRequest<LoginResponse>(endpoints.verifyEmail, {
    method: "POST",
    body: {
      identifier,
      token,
    },
  });

  if (!response.data) {
    throw new Error(response.error || "E-posta dogrulanamadi.");
  }

  setAuthToken(response.data.access_token);
  return mapUser(response.data.user);
}

export async function resendVerification(identifier: string): Promise<RegisterResponse> {
  const response = await apiRequest<RegisterResponse>(endpoints.resendVerification, {
    method: "POST",
    body: {
      identifier,
    },
  });

  if (!response.data) {
    throw new Error(response.error || "Dogrulama kodu gonderilemedi.");
  }

  return response.data;
}

export async function getCurrentUser(): Promise<User> {
  const response = await apiRequest<{ user: ApiUser }>(endpoints.me);
  if (!response.data) {
    throw new Error(response.error || "Kullanici bilgisi alinamadi.");
  }
  return mapUser(response.data.user);
}

export function logout() {
  clearAuthToken();
}

function mapUser(user: ApiUser): User {
  return {
    id: user.id,
    username: user.username,
    email: user.email,
    emailVerified: user.email_verified,
    role: user.role,
    fullName: user.full_name,
    title: user.title,
    profile: user.profile || {},
  };
}
