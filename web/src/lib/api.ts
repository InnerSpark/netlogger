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

export type User = {
  id: number; username: string; role: "admin" | "operator";
  callsign: string | null; license_name: string | null; license_class: string | null;
  verified_by: string | null; license_ok: boolean;
};
export type Net = { id: number; name: string; opened: number; closed: number | null };
export type Checkin = {
  id: number; call: string; name: string; location: string; class: string;
  valid: number | null; first_time: number; flags: string; recheck_done: number; ts: number;
};
export type NetState = { net: Net | null; checkins: Checkin[]; heard: { ts: number; text: string; calls: string | null }[] };
export type Link = { node: string; direction: string; connected_for: string; state: string };
export type NodeState = { enabled: boolean; logger_node: string; default_node: string; links: Link[]; error: string | null };
export type SetupState = {
  version: string; whisper_model: string; transcriber: "starting" | "loading" | "ready";
  last_packet: number | null; last_transmission: number | null;
  usrp_port: number; http_port: number; logger_node: string; default_node: string;
  ami_host: string; ami_port: number; ami_user: string; same_host: boolean;
  node: { configured: boolean; reachable: boolean | null; error: string | null; links: Link[] };
  call_lookup: boolean; cookie_secure: boolean;
};
export type Schedule = {
  id: number; name: string; repeat: "weekly" | "monthly" | "once";
  weekday: number | null; week_of_month: number | null; date: string | null;
  start: string; duration_min: number; node: string | null; disconnect_after: number;
  tz: string; enabled: number; description: string; running_now: boolean; next_start: number | null;
};
export type NetSummary = Net & { schedule_id: number | null; schedule_name: string | null; checkin_count: number };
export type Transmission = { ts: number; seconds: number; text: string; calls: string | null };
export type NetDetail = { net: Net; checkins: Checkin[]; transmissions: Transmission[] };
