export type ChecklistItem = { id: number; code: string; label: string; done: boolean };

export type EventItem = {
  id: number;
  title: string;
  speaker: string;
  starts_at: string;
  duration_minutes: number;
  status: string;
  join_url: string;
  offer_url: string;
  readiness_percent: number;
  is_ready: boolean;
  checklist: ChecklistItem[];
};

export type Me = { username: string; role: "admin" | "organizer" | "host" | null };

export class UnauthorizedError extends Error {}

function csrfToken(): string {
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...init,
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken(), ...init.headers },
  });
  if (response.status === 401) throw new UnauthorizedError();
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return (await response.json()) as T;
}

export const api = {
  me: () => request<Me>("/api/me"),
  events: () => request<EventItem[]>("/api/events/"),
  toggleItem: (eventId: number, itemId: number, done: boolean) =>
    request<EventItem>(`/api/events/${eventId}/checklist/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify({ done }),
    }),
};
