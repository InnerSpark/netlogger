export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// Called when any request comes back 401, so the app can show the login screen
let onUnauthorized: () => void = () => {};
export const setOnUnauthorized = (fn: () => void) => { onUnauthorized = fn; };

async function handle<T>(r: Response): Promise<T> {
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    if (r.status === 401) onUnauthorized();
    throw new ApiError(r.status, body.error || "Request failed. Try again.");
  }
  return body as T;
}

export const get = <T,>(url: string) => fetch(url, { credentials: "same-origin" }).then((r) => handle<T>(r));

export const post = <T = unknown,>(url: string, body: unknown = {}) =>
  fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => handle<T>(r));

export type User = { id: number; username: string; role: "admin" | "operator" };
export type Net = { id: number; name: string; opened: number; closed: number | null };
export type Checkin = {
  id: number; call: string; name: string; location: string; class: string;
  valid: number | null; first_time: number; flags: string; recheck_done: number;
};
export type NetState = { net: Net | null; checkins: Checkin[]; heard: { ts: number; text: string }[] };
export type Link = { node: string; direction: string; connected_for: string; state: string };
export type NodeState = { enabled: boolean; logger_node: string; default_node: string; links: Link[]; error: string | null };
