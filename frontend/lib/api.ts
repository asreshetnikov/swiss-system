import type {
  Participant,
  Pairing,
  Round,
  StandingRow,
  Tournament,
  User,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL
    ? `${process.env.NEXT_PUBLIC_API_URL}/api`
    : "/api";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw Object.assign(new Error(error.detail || "API error"), {
      status: res.status,
      data: error,
    });
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// Auth
export const auth = {
  register: (data: { email: string; password: string; display_name?: string }) =>
    request<User>("/auth/register/", { method: "POST", body: JSON.stringify(data) }),

  login: (data: { email: string; password: string; remember_me?: boolean }) =>
    request<User>("/auth/login/", { method: "POST", body: JSON.stringify(data) }),

  logout: () =>
    request<void>("/auth/logout/", { method: "POST", body: JSON.stringify({}) }),

  refresh: () =>
    request<void>("/auth/refresh/", { method: "POST", body: JSON.stringify({}) }),

  me: () => request<User>("/auth/me/"),
};

// Tournaments
export const tournaments = {
  list: () => request<Tournament[]>("/tournaments/"),

  create: (data: Partial<Tournament>) =>
    request<Tournament>("/tournaments/", { method: "POST", body: JSON.stringify(data) }),

  get: (slug: string) => request<Tournament>(`/tournaments/${slug}/`),

  update: (slug: string, data: Partial<Tournament>) =>
    request<Tournament>(`/tournaments/${slug}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  setStatus: (slug: string, status: string) =>
    request<Tournament>(`/tournaments/${slug}/status/`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),
};

// Participants
export const participants = {
  list: (slug: string) =>
    request<Participant[]>(`/tournaments/${slug}/participants/`),

  create: (slug: string, data: { name: string; rating?: number }) =>
    request<Participant>(`/tournaments/${slug}/participants/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (slug: string, id: number, data: Partial<Participant>) =>
    request<Participant>(`/tournaments/${slug}/participants/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  remove: (slug: string, id: number) =>
    request<void>(`/tournaments/${slug}/participants/${id}/`, {
      method: "DELETE",
    }),

  withdraw: (slug: string, id: number) =>
    request<Participant>(`/tournaments/${slug}/participants/${id}/withdraw/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
};

// Rounds
export const rounds = {
  list: (slug: string) => request<Round[]>(`/tournaments/${slug}/rounds/`),

  generate: (slug: string) =>
    request<Round>(`/tournaments/${slug}/rounds/generate/`, { method: "POST", body: JSON.stringify({}) }),

  publish: (slug: string, number: number) =>
    request<Round>(`/tournaments/${slug}/rounds/${number}/publish/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  getPairings: (slug: string, number: number) =>
    request<Round>(`/tournaments/${slug}/rounds/${number}/pairings/`),

  setResult: (
    slug: string,
    roundNumber: number,
    pairingId: number,
    data: { result: string; note?: string }
  ) =>
    request<Pairing>(
      `/tournaments/${slug}/rounds/${roundNumber}/pairings/${pairingId}/`,
      { method: "PATCH", body: JSON.stringify(data) }
    ),

  close: (slug: string, number: number) =>
    request<Round>(`/tournaments/${slug}/rounds/${number}/close/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
};

// Standings
export const standings = {
  current: (slug: string) =>
    request<{ standings: StandingRow[] }>(`/tournaments/${slug}/standings/`),

  forRound: (slug: string, roundNumber: number) =>
    request<{ standings: StandingRow[]; round: number }>(
      `/tournaments/${slug}/standings/${roundNumber}/`
    ),
};
