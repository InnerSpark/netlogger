import { useCallback, useEffect, useRef, useState } from "react";
import { Radio } from "lucide-react";
import { get, post, setOnUnauthorized, type User } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { AuthScreen, VerifyLicense } from "@/pages/AuthScreen";
import { Dashboard } from "@/pages/Dashboard";
import { Users } from "@/pages/Users";
import { Health } from "@/pages/Health";
import { Stats } from "@/pages/Stats";
import { Nets } from "@/pages/Nets";
import { NetDetail } from "@/pages/NetDetail";
import { PasswordDialog } from "@/components/PasswordDialog";

type Status = { setup_needed: boolean; require_license: boolean; user: User | null };
type View = "dashboard" | "users" | "health" | "stats" | "nets" | `net-${number}`;

const viewFromHash = (): View => {
  const h = window.location.hash;
  const m = h.match(/^#\/nets\/(\d+)$/);
  if (m) return `net-${Number(m[1])}`;
  return h === "#/users" ? "users" : ["#/health", "#/status", "#/setup"].includes(h) ? "health" : h === "#/nets" ? "nets" : h === "#/stats" ? "stats" : "dashboard";
};

export default function App() {
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState("");
  const [view, setView] = useState<View>(viewFromHash);

  const load = useCallback(async () => {
    try {
      setStatus(await get<Status>("/api/auth/status"));
      setError("");
    } catch {
      setError("Can't reach the logger. Is it running?");
    }
  }, []);

  useEffect(() => {
    load();
    setOnUnauthorized(() => setStatus((s) => (s ? { ...s, user: null } : s)));
  }, [load]);

  // Hash routing so the back button works
  useEffect(() => {
    const on = () => setView(viewFromHash());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);

  // Move focus to the page heading when the page changes or after logging in,
  // so screen readers announce where you landed
  const userId = status?.user?.id;
  const shown = (view === "users" || view === "health") && status?.user?.role !== "admin" ? "dashboard" : view;
  const initial = useRef(true);
  const loaded = !!status;
  useEffect(() => {
    if (!loaded) return;
    if (initial.current) {
      initial.current = false;
      if (userId) return; // opened the page already logged in: leave focus alone
    }
    if (!userId) return;
    requestAnimationFrame(() => document.querySelector<HTMLElement>("main h1")?.focus());
  }, [shown, userId, loaded]);

  if (error) {
    return (
      <main className="mx-auto max-w-md px-4 py-16">
        <p role="alert" className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-destructive">{error}</p>
        <Button className="mt-4" variant="outline" onClick={load}>Try again</Button>
      </main>
    );
  }
  if (!status) return <main className="px-4 py-16 text-center text-muted-foreground">Loading…</main>;
  // After the first admin is created, land on the Health page
  if (status.setup_needed) return <AuthScreen mode="setup" requireLicense={status.require_license} onDone={() => { window.location.hash = "#/health"; setView("health"); load(); }} />;
  if (!status.user) return <AuthScreen mode="login" onDone={load} />;

  const user = status.user;
  if (!user.license_ok) {
    return <VerifyLicense user={user} onDone={load} onLogout={async () => { await post("/api/auth/logout").catch(() => {}); load(); }} />;
  }
  const current: View = (view === "users" || view === "health") && user.role !== "admin" ? "dashboard" : view;

  const logout = async () => {
    await post("/api/auth/logout").catch(() => {});
    load();
  };

  return (
    <>
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:ring-[3px] focus:ring-ring/50"
        onClick={(e) => { e.preventDefault(); document.querySelector<HTMLElement>("main h1")?.focus(); }}>
        Skip to content
      </a>
      <header className="border-b">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <span className="flex items-center gap-2 font-semibold">
            <Radio aria-hidden="true" className="size-5" />
            Net Logger
          </span>
          <nav aria-label="Main" className="flex gap-1">
            <Button asChild variant={current === "dashboard" ? "secondary" : "ghost"} size="sm">
              <a href="#/" aria-current={current === "dashboard" ? "page" : undefined}>Dashboard</a>
            </Button>
            <Button asChild variant={current === "nets" || current.startsWith("net-") ? "secondary" : "ghost"} size="sm">
              <a href="#/nets" aria-current={current === "nets" ? "page" : undefined}>Nets</a>
            </Button>
            <Button asChild variant={current === "stats" ? "secondary" : "ghost"} size="sm">
              <a href="#/stats" aria-current={current === "stats" ? "page" : undefined}>Stats</a>
            </Button>
            {user.role === "admin" && (
              <>
                <Button asChild variant={current === "health" ? "secondary" : "ghost"} size="sm">
                  <a href="#/health" aria-current={current === "health" ? "page" : undefined}>Health</a>
                </Button>
                <Button asChild variant={current === "users" ? "secondary" : "ghost"} size="sm">
                  <a href="#/users" aria-current={current === "users" ? "page" : undefined}>Users</a>
                </Button>
              </>
            )}
          </nav>
          <div className="ml-auto flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">
              <span className="sr-only">Signed in as </span>{user.callsign || user.username}
              <span className="sr-only">, {user.role}</span>
            </span>
            <PasswordDialog />
            <Button variant="outline" size="sm" onClick={logout}>Log out</Button>
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-6xl px-4 py-6">
        {current === "users" ? <Users me={user} />
          : current === "health" ? <Health />
          : current === "nets" ? <Nets />
          : current === "stats" ? <Stats />
          : current.startsWith("net-") ? <NetDetail key={current} id={Number(current.slice(4))} />
          : <Dashboard admin={user.role === "admin"} />}
      </main>
    </>
  );
}
