import { useCallback, useEffect, useRef, useState, type FormEvent, type RefObject } from "react";
import { Check, Download } from "lucide-react";
import { get, post, type Checkin, type NetState } from "@/lib/api";
import { NodePanel } from "@/components/NodePanel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Toggle } from "@/components/ui/toggle";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

const FLAGS = [
  { key: "traffic", label: "Traffic" },
  { key: "short_time", label: "Short time" },
  { key: "recheck", label: "Recheck" },
] as const;

const flagsOf = (c: Checkin) => (c.flags || "").split(",").filter(Boolean);
const spell = (call: string) => call.split("").join(" ");
const timeOf = (ts: number) => new Date(ts * 1000).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

// Below Tailwind's md breakpoint, check-ins show as cards with big tap targets
function useIsPhone() {
  const mq = () => window.matchMedia("(max-width: 767px)");
  const [phone, setPhone] = useState(() => mq().matches);
  useEffect(() => {
    const m = mq();
    const on = () => setPhone(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return phone;
}

export function Dashboard() {
  const [state, setState] = useState<NetState | null>(null);
  const [offline, setOffline] = useState(false);
  const [announce, setAnnounce] = useState("");
  const known = useRef<Set<number> | null>(null);
  const rosterHeading = useRef<HTMLHeadingElement>(null);
  const recheckHeading = useRef<HTMLHeadingElement>(null);
  const phone = useIsPhone();

  const refresh = useCallback(async () => {
    try {
      const s = await get<NetState>("/api/state");
      if (known.current) {
        const fresh = s.checkins.filter((c) => !known.current!.has(c.id));
        if (fresh.length)
          setAnnounce("New check-in: " + fresh
            .map((c) => [spell(c.call), c.name, c.first_time ? "first time" : ""].filter(Boolean).join(", "))
            .join("; "));
      }
      known.current = new Set(s.checkins.map((c) => c.id));
      setState(s);
      setOffline(false);
    } catch {
      setOffline(true);
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 2000);
    return () => clearInterval(t);
  }, [refresh]);

  const net = state?.net ?? null;
  const open = !!net && !net.closed;
  const checkins = state?.checkins ?? [];
  const recheck = checkins.filter((c) => flagsOf(c).includes("recheck") && !c.recheck_done);

  const setFlags = async (c: Checkin, key: string, on: boolean) => {
    const f = new Set(flagsOf(c));
    if (on) f.add(key); else f.delete(key);
    await post(`/api/checkin/${c.id}`, { flags: [...f] });
    refresh();
  };

  const remove = async (c: Checkin) => {
    await post(`/api/checkin/${c.id}`, { delete: true });
    refresh();
  };

  const markDone = async (c: Checkin) => {
    await post(`/api/checkin/${c.id}`, { recheck_done: 1 });
    await refresh();
    recheckHeading.current?.focus();
  };

  const flagToggles = (c: Checkin) => FLAGS.map((f) => {
    const on = flagsOf(c).includes(f.key);
    return (
      <Toggle key={f.key} variant="outline" size={phone ? "lg" : "sm"} pressed={on}
        className={phone ? "h-11" : undefined}
        onPressedChange={(v) => setFlags(c, f.key, v)} aria-label={`${f.label} for ${spell(c.call)}`}>
        {on && <Check aria-hidden="true" />}{f.label}
      </Toggle>
    );
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 tabIndex={-1} className="text-2xl font-semibold tracking-tight outline-none">Dashboard</h1>
        <p className="flex flex-wrap items-center gap-2 text-muted-foreground" role="status">
          {!state ? "Loading…" : open ? (
            <><Badge>Logging</Badge><span><strong className="text-foreground">{net!.name}</strong> is open.</span></>
          ) : (
            <><Badge variant="outline">Not logging</Badge><span>{net ? <>Last net: <strong className="text-foreground">{net.name}</strong> (closed).</> : "No net yet."}</span></>
          )}
        </p>
        {offline && (
          <p role="alert" className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            Lost connection to the logger. Retrying…
          </p>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <NetControls open={open} netName={net?.name} onChange={refresh} />
        <NodePanel />
        <AddCheckin open={open} onAdded={refresh} />
      </div>

      <section aria-labelledby="h-roster" className="flex flex-col gap-3">
        <h2 id="h-roster" ref={rosterHeading} tabIndex={-1} className="text-xl font-semibold outline-none">
          Check-ins <span className="font-normal text-muted-foreground">({checkins.length})</span>
        </h2>
        {!state ? (
          <p className="text-muted-foreground">Loading…</p>
        ) : checkins.length === 0 ? (
          <p className="rounded-xl border border-dashed px-4 py-8 text-center text-muted-foreground">
            {open ? "No check-ins yet. They show up here as stations call in." : "Open a net to start logging."}
          </p>
        ) : phone ? (
          <ol className="flex flex-col gap-3">
            {checkins.map((c, i) => (
              <li key={c.id}>
                <Card className="gap-3 py-4">
                  <CardContent className="flex flex-col gap-3 px-4">
                    <div className="flex flex-col gap-1">
                      <h3 className="flex flex-wrap items-center gap-2 text-lg font-semibold">
                        <span className="font-normal text-muted-foreground">{i + 1}.</span>
                        <span className="font-mono">{c.call}</span>
                        <CallTags c={c} />
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        {[c.name, c.location, c.class].filter(Boolean).join(" · ") || "No details"}
                      </p>
                    </div>
                    <div className="grid grid-cols-3 gap-2">{flagToggles(c)}</div>
                    <div className="grid grid-cols-2 gap-2">
                      <FixCall c={c} onDone={refresh} phone />
                      <RemoveCall c={c} onConfirm={remove} phone returnFocus={rosterHeading} />
                    </div>
                  </CardContent>
                </Card>
              </li>
            ))}
          </ol>
        ) : (
          <div className="rounded-xl border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col" className="pl-4">#</TableHead>
                  <TableHead scope="col">Call</TableHead>
                  <TableHead scope="col">Name</TableHead>
                  <TableHead scope="col">Location</TableHead>
                  <TableHead scope="col">Class</TableHead>
                  <TableHead scope="col">Flags</TableHead>
                  <TableHead scope="col" className="pr-4"><span className="sr-only">Actions</span></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {checkins.map((c, i) => (
                  <TableRow key={c.id}>
                    <TableCell className="pl-4 text-muted-foreground">{i + 1}</TableCell>
                    <TableCell>
                      <span className="flex items-center gap-2">
                        <span className="font-mono text-base font-semibold">{c.call}</span>
                        <CallTags c={c} />
                      </span>
                    </TableCell>
                    <TableCell>{c.name}</TableCell>
                    <TableCell>{c.location}</TableCell>
                    <TableCell>{c.class}</TableCell>
                    <TableCell><div className="flex gap-1">{flagToggles(c)}</div></TableCell>
                    <TableCell className="pr-4">
                      <div className="flex justify-end gap-1">
                        <FixCall c={c} onDone={refresh} />
                        <RemoveCall c={c} onConfirm={remove} returnFocus={rosterHeading} />
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="gap-4">
          <CardHeader>
            <CardTitle ref={recheckHeading} tabIndex={-1} className="outline-none" id="h-recheck">
              Recheck list <span className="font-normal text-muted-foreground">({recheck.length})</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {recheck.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nobody waiting.</p>
            ) : (
              <ul aria-labelledby="h-recheck" className="flex flex-col divide-y">
                {recheck.map((c) => (
                  <li key={c.id} className="flex items-center justify-between gap-3 py-2">
                    <span><span className="font-mono font-semibold">{c.call}</span> {c.name}</span>
                    <Button variant="outline" size="sm" className="max-md:h-11" onClick={() => markDone(c)}
                      aria-label={`Mark ${spell(c.call)} recheck done`}>
                      Mark done
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="gap-4">
          <CardHeader><CardTitle id="h-heard">Last heard</CardTitle></CardHeader>
          <CardContent>
            {!state?.heard.length ? (
              <p className="text-sm text-muted-foreground">Nothing heard yet.</p>
            ) : (
              <ul aria-labelledby="h-heard" className="flex flex-col divide-y text-sm">
                {state.heard.map((h, i) => (
                  <li key={`${h.ts}-${i}`} className="py-2">
                    <span className="font-medium">{timeOf(h.ts)}</span>{" "}
                    <span className="text-muted-foreground">{h.text}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <div aria-live="polite" className="sr-only">{announce}</div>
    </div>
  );
}

function CallTags({ c }: { c: Checkin }) {
  return (
    <>
      {!!c.first_time && <Badge variant="secondary">First time</Badge>}
      {c.valid === 0 && <Badge variant="destructive">Not found</Badge>}
    </>
  );
}

function NetControls({ open, netName, onChange }: { open: boolean; netName?: string; onChange: () => void }) {
  const [name, setName] = useState("");

  const openNet = async (e: FormEvent) => {
    e.preventDefault();
    await post("/api/net/open", { name: name.trim() });
    setName("");
    onChange();
  };

  return (
    <Card className="gap-4">
      <CardHeader><CardTitle>Net</CardTitle></CardHeader>
      <CardContent>
        {open ? (
          <div className="flex flex-wrap gap-2">
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" className="max-md:h-11 max-md:flex-1">Close net</Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Close {netName}?</AlertDialogTitle>
                  <AlertDialogDescription>Logging stops. The check-in list stays and can still be exported.</AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Keep logging</AlertDialogCancel>
                  <AlertDialogAction variant="destructive" onClick={async () => { await post("/api/net/close"); onChange(); }}>
                    Close net
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
            <ExportButton />
          </div>
        ) : (
          <form onSubmit={openNet} className="flex flex-col gap-2">
            <Label htmlFor="net-name">Net name</Label>
            <Input id="net-name" value={name} onChange={(e) => setName(e.target.value)}
              placeholder="Tuesday Night Net" className="max-md:h-11" />
            <div className="flex flex-wrap gap-2">
              <Button type="submit" className="max-md:h-11 max-md:flex-1">Open net</Button>
              <ExportButton />
            </div>
          </form>
        )}
      </CardContent>
    </Card>
  );
}

function ExportButton() {
  return (
    <Button variant="outline" asChild className="max-md:h-11 max-md:flex-1">
      <a href="/api/export.csv"><Download aria-hidden="true" />Export CSV</a>
    </Button>
  );
}

function AddCheckin({ open, onAdded }: { open: boolean; onAdded: () => void }) {
  const [call, setCall] = useState("");
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      if (!open) throw new Error("Open a net first.");
      if (!call.trim()) throw new Error("Enter a callsign.");
      await post("/api/checkin", { call: call.trim() });
      setCall("");
      setError("");
      onAdded();
    } catch (err) {
      setError((err as Error).message);
      input.current?.focus();
    }
  };

  return (
    <Card className="gap-4">
      <CardHeader><CardTitle>Add check-in by hand</CardTitle></CardHeader>
      <CardContent>
        <form onSubmit={submit} noValidate className="flex flex-col gap-2">
          <Label htmlFor="add-call">Callsign</Label>
          <div className="flex gap-2 max-md:flex-col">
            <Input ref={input} id="add-call" value={call} autoComplete="off" autoCapitalize="characters" spellCheck={false}
              onChange={(e) => setCall(e.target.value)} aria-invalid={!!error || undefined}
              aria-describedby="add-error" className="font-mono uppercase md:flex-1 max-md:h-11" />
            <Button type="submit" className="max-md:h-11">Add</Button>
          </div>
          <p id="add-error" role="alert" className="min-h-5 text-sm font-medium text-destructive">{error}</p>
        </form>
      </CardContent>
    </Card>
  );
}

function FixCall({ c, onDone, phone }: { c: Checkin; onDone: () => void; phone?: boolean }) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState(c.call);
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await post(`/api/checkin/${c.id}`, { call: value.trim() });
      setOpen(false);
      onDone();
    } catch (err) {
      setError((err as Error).message);
      input.current?.focus();
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { setValue(c.call); setError(""); } }}>
      <DialogTrigger asChild>
        <Button variant="outline" size={phone ? "lg" : "sm"} className={phone ? "h-11" : undefined}
          aria-label={`Fix callsign ${spell(c.call)}`}>Fix call</Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={save} noValidate className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Fix callsign</DialogTitle>
            <DialogDescription>Logged as <span className="font-mono font-semibold">{c.call}</span>. Saving redoes the name lookup.</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Label htmlFor={`fix-${c.id}`}>Correct callsign</Label>
            <Input ref={input} id={`fix-${c.id}`} value={value} autoComplete="off" autoCapitalize="characters" spellCheck={false}
              onChange={(e) => setValue(e.target.value)} aria-invalid={!!error || undefined}
              aria-describedby={`fix-${c.id}-error`} className="font-mono uppercase" />
            <p id={`fix-${c.id}-error`} role="alert" className="min-h-5 text-sm font-medium text-destructive">{error}</p>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit">Save</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function RemoveCall({ c, onConfirm, phone, returnFocus }: {
  c: Checkin; onConfirm: (c: Checkin) => void; phone?: boolean; returnFocus: RefObject<HTMLHeadingElement | null>;
}) {
  const removed = useRef(false);
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="ghost" size={phone ? "lg" : "sm"} className={`text-destructive hover:text-destructive ${phone ? "h-11" : ""}`}
          aria-label={`Remove ${spell(c.call)}`}>Remove</Button>
      </AlertDialogTrigger>
      <AlertDialogContent onCloseAutoFocus={(e) => {
        // The row is gone after a remove, so send focus to the list heading
        if (removed.current) { e.preventDefault(); returnFocus.current?.focus(); }
      }}>
        <AlertDialogHeader>
          <AlertDialogTitle>Remove {c.call}?</AlertDialogTitle>
          <AlertDialogDescription>This takes {c.call} off this net's check-in list.</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Keep</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={() => { removed.current = true; onConfirm(c); }}>Remove</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
