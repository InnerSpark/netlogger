import { useRef, useState, type FormEvent } from "react";
import { Radio } from "lucide-react";
import { post } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

// First run creates the admin account. After that it's a login form.
export function AuthScreen({ mode, onDone }: { mode: "setup" | "login"; onDone: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [errField, setErrField] = useState<"username" | "password" | null>(null);
  const [busy, setBusy] = useState(false);
  const userRef = useRef<HTMLInputElement>(null);
  const passRef = useRef<HTMLInputElement>(null);
  const setup = mode === "setup";

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!username.trim()) { setError("Enter a username."); setErrField("username"); userRef.current?.focus(); return; }
    if (!password) { setError("Enter a password."); setErrField("password"); passRef.current?.focus(); return; }
    setBusy(true);
    try {
      await post(setup ? "/api/auth/setup" : "/api/auth/login", { username, password });
      onDone();
    } catch (err) {
      const msg = (err as Error).message;
      setError(msg);
      if (msg.startsWith("Username")) {
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
            {setup ? "Create the first admin account. You can add net control operators after." : "Use the account your logger admin gave you."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} noValidate className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="username">Username</Label>
              <Input ref={userRef} id="username" autoComplete="username" autoCapitalize="none" spellCheck={false}
                value={username} onChange={(e) => setUsername(e.target.value)} className="max-md:h-11"
                aria-invalid={errField === "username" || undefined} aria-describedby="auth-error" autoFocus />
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
