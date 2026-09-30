import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { get, post, type User } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

const ROLE_HELP = "Operators run nets and connect nodes. Admins also manage users.";

export function Users({ me }: { me: User }) {
  const [users, setUsers] = useState<User[] | null>(null);
  const [error, setError] = useState("");
  const [announce, setAnnounce] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);

  const load = useCallback(async () => {
    try {
      setUsers((await get<{ users: User[] }>("/api/users")).users);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const update = async (u: User, body: Record<string, unknown>, message: string) => {
    try {
      setUsers((await post<{ users: User[] }>(`/api/users/${u.id}`, body)).users);
      setError("");
      setAnnounce(message);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold tracking-tight outline-none">Users</h1>
        <p className="text-muted-foreground">{ROLE_HELP}</p>
      </div>

      {error && <p role="alert" className="rounded-md border border-destructive/50 bg-background px-3 py-2 text-sm text-destructive">{error}</p>}

      <div className="grid gap-4 lg:grid-cols-[1fr_22rem]">
        <div className="min-w-0 rounded-xl border bg-card">
          {!users ? (
            <p className="p-4 text-muted-foreground">Loading…</p>
          ) : (
            <Table label="Users">
              <TableHeader>
                <TableRow>
                  <TableHead scope="col" className="pl-4">Callsign</TableHead>
                  <TableHead scope="col">Name</TableHead>
                  <TableHead scope="col">Username</TableHead>
                  <TableHead scope="col">Role</TableHead>
                  <TableHead scope="col">License</TableHead>
                  <TableHead scope="col" className="pr-4"><span className="sr-only">Actions</span></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell className="pl-4 font-mono font-semibold">
                      {u.callsign || "-"}{u.id === me.id && <span className="ml-2 font-sans font-normal text-muted-foreground">(you)</span>}
                    </TableCell>
                    <TableCell>{u.license_name}{u.license_class && <span className="text-muted-foreground"> · {u.license_class}</span>}</TableCell>
                    <TableCell>{u.username}</TableCell>
                    <TableCell><Badge variant={u.role === "admin" ? "default" : "secondary"}>{u.role === "admin" ? "Admin" : "Operator"}</Badge></TableCell>
                    <TableCell>
                      {!u.license_ok ? <Badge variant="destructive">Not verified</Badge>
                        : u.verified_by === "callook" ? <span className="text-muted-foreground">FCC checked</span>
                        : u.verified_by === "self" ? <span className="text-muted-foreground">Self-entered (first admin)</span>
                        : u.verified_by ? <span className="text-muted-foreground">Checked by {u.verified_by.replace("admin:", "")}</span>
                        : <span className="text-muted-foreground">Not required</span>}
                    </TableCell>
                    <TableCell className="pr-4">
                      <div className="flex justify-end gap-1">
                        {u.id !== me.id && (
                          <Button variant="outline" size="sm" className="max-md:h-11"
                            onClick={() => update(u, { role: u.role === "admin" ? "operator" : "admin" },
                              `${u.username} is now ${u.role === "admin" ? "an operator" : "an admin"}.`)}>
                            {u.role === "admin" ? "Make operator" : "Make admin"}
                          </Button>
                        )}
                        <ResetPassword user={u} onDone={(msg) => { setAnnounce(msg); load(); }} />
                        {u.id !== me.id && (
                          <DeleteUser user={u} onConfirm={() => update(u, { delete: true }, `${u.callsign || u.username} deleted.`)} returnFocus={heading} />
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
        <AddUser onAdded={(list, name) => { setUsers(list); setAnnounce(`${name} added.`); }} />
      </div>
      <div aria-live="polite" className="sr-only">{announce}</div>
    </div>
  );
}

function AddUser({ onAdded }: { onAdded: (users: User[], name: string) => void }) {
  const [callsign, setCallsign] = useState("");
  const [manual, setManual] = useState(false);
  const callRef = useRef<HTMLInputElement>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"operator" | "admin">("operator");
  const [error, setError] = useState("");
  const userRef = useRef<HTMLInputElement>(null);
  const passRef = useRef<HTMLInputElement>(null);
  const field = !error ? null : error.startsWith("Password") ? "password"
    : error.startsWith("Username") || error.includes("username") ? "username" : "callsign";

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const r = await post<{ users: User[] }>("/api/users", { callsign: callsign.trim(), username: username.trim(), password, role, manual });
      onAdded(r.users, callsign.trim().toUpperCase() || username.trim());
      setCallsign(""); setUsername(""); setPassword(""); setRole("operator"); setManual(false); setError("");
      callRef.current?.focus();
    } catch (err) {
      const msg = (err as Error).message;
      setError(msg);
      (msg.startsWith("Password") ? passRef : msg.startsWith("Username") || msg.includes("username") ? userRef : callRef).current?.focus();
    }
  };

  return (
    <Card className="gap-4 self-start">
      <CardHeader>
        <CardTitle>Add a user</CardTitle>
        <CardDescription>Their callsign is checked against the FCC license database. Give them the password; they can change it after they log in.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} noValidate className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="new-callsign">Callsign</Label>
            <Input ref={callRef} id="new-callsign" autoComplete="off" autoCapitalize="characters" spellCheck={false}
              value={callsign} onChange={(e) => setCallsign(e.target.value)} className="font-mono uppercase max-md:h-11"
              aria-invalid={field === "callsign" || undefined} aria-describedby="new-user-error" />
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" checked={manual} onChange={(e) => setManual(e.target.checked)}
                className="mt-0.5 size-4 accent-primary" />
              <span>I checked this license myself <span className="text-muted-foreground">(calls from outside the US, or when the FCC lookup is down)</span></span>
            </label>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="new-username">Username (optional)</Label>
            <Input ref={userRef} id="new-username" autoComplete="off" autoCapitalize="none" spellCheck={false}
              value={username} onChange={(e) => setUsername(e.target.value)} className="max-md:h-11"
              aria-invalid={field === "username" || undefined} aria-describedby="new-user-hint new-user-error" />
            <p id="new-user-hint" className="text-sm text-muted-foreground">Leave blank to use their callsign.</p>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="new-password">Temporary password</Label>
            <Input ref={passRef} id="new-password" type="password" autoComplete="new-password"
              value={password} onChange={(e) => setPassword(e.target.value)} className="max-md:h-11"
              aria-invalid={field === "password" || undefined} aria-describedby="new-pw-hint new-user-error" />
            <p id="new-pw-hint" className="text-sm text-muted-foreground">At least 10 characters.</p>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="new-role">Role</Label>
            <NativeSelect id="new-role" value={role} onChange={(e) => setRole(e.target.value as "operator" | "admin")} className="max-md:h-11">
              <option value="operator">Operator</option>
              <option value="admin">Admin</option>
            </NativeSelect>
          </div>
          <p id="new-user-error" role="alert" className="min-h-5 text-sm font-medium text-destructive">{error}</p>
          <Button type="submit" className="max-md:h-11">Add user</Button>
        </form>
      </CardContent>
    </Card>
  );
}

function ResetPassword({ user, onDone }: { user: User; onDone: (msg: string) => void }) {
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await post(`/api/users/${user.id}`, { password });
      setOpen(false);
      onDone(`Password reset for ${user.username}.`);
    } catch (err) {
      setError((err as Error).message);
      input.current?.focus();
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { setPassword(""); setError(""); } }}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="max-md:h-11" aria-label={`Reset password for ${user.username}`}>Reset password</Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={save} noValidate className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Reset password for {user.username}</DialogTitle>
            <DialogDescription>They get logged out everywhere and use this password next time.</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Label htmlFor={`reset-${user.id}`}>New password</Label>
            <Input ref={input} id={`reset-${user.id}`} type="password" autoComplete="new-password"
              value={password} onChange={(e) => setPassword(e.target.value)}
              aria-invalid={!!error || undefined} aria-describedby={`reset-${user.id}-error`} />
            <p id={`reset-${user.id}-error`} role="alert" className="min-h-5 text-sm font-medium text-destructive">{error}</p>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit">Reset password</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function DeleteUser({ user, onConfirm, returnFocus }: {
  user: User; onConfirm: () => void; returnFocus: React.RefObject<HTMLHeadingElement | null>;
}) {
  const deleted = useRef(false);
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive max-md:h-11"
          aria-label={`Delete ${user.username}`}>Delete</Button>
      </AlertDialogTrigger>
      <AlertDialogContent onCloseAutoFocus={(e) => {
        if (deleted.current) { e.preventDefault(); returnFocus.current?.focus(); }
      }}>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete {user.username}?</AlertDialogTitle>
          <AlertDialogDescription>They lose access right away. Net logs stay.</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Keep</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={() => { deleted.current = true; onConfirm(); }}>Delete</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
