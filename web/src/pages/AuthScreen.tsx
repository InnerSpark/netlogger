import { useRef, useState, type FormEvent } from "react";
import { Radio } from "lucide-react";
import { post, type User } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

// First run creates the admin account. After that it's a login form.
export function AuthScreen({ mode, onDone, requireLicense = true }: { mode: "setup" | "login"; onDone: () => void; requireLicense?: boolean }) {
  const [username, setUsername] = useState("");
  const [callsign, setCallsign] = useState("");
  const callRef = useRef<HTMLInputElement>(null);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [errField, setErrField] = useState<"username" | "password" | "callsign" | null>(null);
  const [busy, setBusy] = useState(false);
  const userRef = useRef<HTMLInputElement>(null);
  const passRef = useRef<HTMLInputElement>(null);
  const setup = mode === "setup";

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (setup && requireLicense && !callsign.trim()) { setError("Enter your callsign."); setErrField("callsign"); callRef.current?.focus(); return; }
    if (!setup && !username.trim()) { setError("Enter a username."); setErrField("username"); userRef.current?.focus(); return; }
    if (!password) { setError("Enter a password."); setErrField("password"); passRef.current?.focus(); return; }
    setBusy(true);
    try {
      await post(setup ? "/api/auth/setup" : "/api/auth/login", setup ? { username, password, callsign } : { username, password });
      onDone();
    } catch (err) {
      const msg = (err as Error).message;
      setError(msg);
      if (setup && !msg.startsWith("Username") && !msg.startsWith("Password") && !msg.startsWith("Can't reach")) {
        setErrField("callsign");
        callRef.current?.focus();
      } else if (msg.startsWith("Username")) {
        setErrField("username");
        userRef.current?.focus();
      } else {
        setErrField("password");
        setPassword("");
        passRef.current?.focus();
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="flex min-h-svh items-center justify-center px-4 py-10">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <h1 tabIndex={-1} className="flex items-center gap-2 text-xl font-semibold outline-none">
            <Radio aria-hidden="true" className="size-5" />
            {setup ? "Set up Net Logger" : "Log in to Net Logger"}
          </h1>
          <CardDescription>
            {setup
              ? requireLicense
                ? "Create the first admin account. Your callsign is checked against the FCC license database."
                : "Create the first admin account. You can add net control operators after."
              : "Use the account your logger admin gave you."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} noValidate className="flex flex-col gap-4">
            {setup && (
              <div className="flex flex-col gap-2">
                <Label htmlFor="callsign">Callsign{!requireLicense && " (optional)"}</Label>
                <Input ref={callRef} id="callsign" autoComplete="off" autoCapitalize="characters" spellCheck={false}
                  value={callsign} onChange={(e) => setCallsign(e.target.value)} className="font-mono uppercase max-md:h-11"
                  aria-invalid={errField === "callsign" || undefined} aria-describedby="auth-error" autoFocus />
              </div>
            )}
            <div className="flex flex-col gap-2">
              <Label htmlFor="username">Username{setup && " (optional)"}</Label>
              <Input ref={userRef} id="username" autoComplete="username" autoCapitalize="none" spellCheck={false}
                value={username} onChange={(e) => setUsername(e.target.value)} className="max-md:h-11"
                aria-invalid={errField === "username" || undefined}
                aria-describedby={setup ? "user-hint auth-error" : "auth-error"} autoFocus={!setup} />
              {setup && <p id="user-hint" className="text-muted-foreground text-sm">Leave blank to log in with your callsign.</p>}
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Password</Label>
              <Input ref={passRef} id="password" type="password" autoComplete={setup ? "new-password" : "current-password"}
                value={password} onChange={(e) => setPassword(e.target.value)} className="max-md:h-11"
                aria-invalid={errField === "password" || undefined}
                aria-describedby={setup ? "pw-hint auth-error" : "auth-error"} />
              {setup && <p id="pw-hint" className="text-muted-foreground text-sm">At least 10 characters.</p>}
            </div>
            <p id="auth-error" role="alert" className="min-h-5 text-sm font-medium text-destructive">{error}</p>
            <Button type="submit" disabled={busy} className="max-md:h-11">
              {setup ? "Create admin account" : "Log in"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}


// Shown when an account has no verified license: made before license checks, or it expired
export function VerifyLicense({ user, onDone, onLogout }: { user: User; onDone: () => void; onLogout: () => void }) {
  const [callsign, setCallsign] = useState(user.callsign || "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLInputElement>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!callsign.trim()) { setError("Enter your callsign."); ref.current?.focus(); return; }
    setBusy(true);
    try {
      await post("/api/me/license", { callsign });
      onDone();
    } catch (err) {
      setError((err as Error).message);
      ref.current?.focus();
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="flex min-h-svh items-center justify-center px-4 py-10">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <h1 className="flex items-center gap-2 text-xl font-semibold">
            <Radio aria-hidden="true" className="size-5" />
            Verify your license
          </h1>
          <CardDescription>
            {user.callsign
              ? `The license for ${user.callsign} couldn't be confirmed. It may have expired. Enter a current callsign to keep using Net Logger.`
              : "Net Logger accounts are for licensed amateur radio operators. Enter your callsign to check it against the FCC license database."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} noValidate className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="verify-call">Callsign</Label>
              <Input ref={ref} id="verify-call" autoComplete="off" autoCapitalize="characters" spellCheck={false}
                value={callsign} onChange={(e) => setCallsign(e.target.value)} className="font-mono uppercase max-md:h-11"
                aria-invalid={!!error || undefined} aria-describedby="verify-error" autoFocus />
            </div>
            <p id="verify-error" role="alert" className="min-h-5 text-sm font-medium text-destructive">{error}</p>
            <Button type="submit" disabled={busy} className="max-md:h-11">Verify</Button>
            <p className="text-sm text-muted-foreground">
              Licensed outside the US? Ask your logger admin to verify you.{" "}
              <button type="button" onClick={onLogout} className="font-medium text-foreground underline underline-offset-4 cursor-pointer">Log out</button>
            </p>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
