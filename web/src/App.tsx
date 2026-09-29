import { useCallback, useEffect, useState } from "react";
import { Radio } from "lucide-react";
import { get, post, setOnUnauthorized, type User } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { AuthScreen } from "@/pages/AuthScreen";
import { Dashboard } from "@/pages/Dashboard";
import { Users } from "@/pages/Users";
import { PasswordDialog } from "@/components/PasswordDialog";

type Status = { setup_needed: boolean; user: User | null };
type View = "dashboard" | "users";

const viewFromHash = (): View => (window.location.hash === "#/users" ? "users" : "dashboard");

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

  // Hash routing so the back button works; focus the new page's heading on change
  useEffect(() => {
    const on = () => {
      setView(viewFromHash());
      requestAnimationFrame(() => document.querySelector<HTMLElement>("main h1")?.focus());
    };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);

  if (error) {
    return (
      <main className="mx-auto max-w-md px-4 py-16">
        <p role="alert" className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-destructive">{error}</p>
        <Button className="mt-4" variant="outline" onClick={load}>Try again</Button>
      </main>
    );
  }
  if (!status) return <main className="px-4 py-16 text-center text-muted-foreground">Loading…</main>;
  if (status.setup_needed) return <AuthScreen mode="setup" onDone={load} />;
  if (!status.user) return <AuthScreen mode="login" onDone={load} />;

  const user = status.user;
  const current = view === "users" && user.role === "admin" ? "users" : "dashboard";

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
            {user.role === "admin" && (
              <Button asChild variant={current === "users" ? "secondary" : "ghost"} size="sm">
                <a href="#/users" aria-current={current === "users" ? "page" : undefined}>Users</a>
              </Button>
            )}
          </nav>
          <div className="ml-auto flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">
              <span className="sr-only">Signed in as </span>{user.username}
              <span className="sr-only">, {user.role}</span>
            </span>
            <PasswordDialog />
            <Button variant="outline" size="sm" onClick={logout}>Log out</Button>
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-6xl px-4 py-6">
        {current === "users" ? <Users me={user} /> : <Dashboard />}
      </main>
    </>
  );
}
