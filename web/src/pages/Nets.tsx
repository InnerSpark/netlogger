import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { CalendarPlus, Download, FileText } from "lucide-react";
import { get, post, type NetSummary, type NodeState, type Schedule } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
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

const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const WEEKS: [number, string][] = [[1, "First"], [2, "Second"], [3, "Third"], [4, "Fourth"], [-1, "Last"]];

export const when = (ts: number) =>
  new Date(ts * 1000).toLocaleString([], { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
const length = (a: number, b: number | null) => (b ? `${Math.max(1, Math.round((b - a) / 60))} min` : "Open now");

export function Nets() {
  const [schedules, setSchedules] = useState<Schedule[] | null>(null);
  const [nets, setNets] = useState<NetSummary[] | null>(null);
  const [error, setError] = useState("");
  const [announce, setAnnounce] = useState("");
  const [defaultNode, setDefaultNode] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);

  const load = useCallback(async () => {
    try {
      const [s, n] = await Promise.all([get<{ schedules: Schedule[] }>("/api/schedules"), get<{ nets: NetSummary[] }>("/api/nets")]);
      setSchedules(s.schedules);
      setNets(n.nets);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
    get<NodeState>("/api/nodes").then((n) => setDefaultNode(n.default_node)).catch(() => {});
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [load]);

  const toggle = async (s: Schedule) => {
    setSchedules((await post<{ schedules: Schedule[] }>(`/api/schedules/${s.id}`, { enabled: !s.enabled })).schedules);
    setAnnounce(`${s.name} ${s.enabled ? "paused" : "turned on"}.`);
  };

  const remove = async (s: Schedule) => {
    setSchedules((await post<{ schedules: Schedule[] }>(`/api/schedules/${s.id}`, { delete: true })).schedules);
    setAnnounce(`${s.name} schedule deleted.`);
  };

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-1">
        <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold tracking-tight outline-none">Nets</h1>
        <p className="text-muted-foreground">Schedule nets to open on their own, and look back at past nets.</p>
      </div>

      {error && <p role="alert" className="rounded-md border border-destructive/50 bg-background px-3 py-2 text-sm text-destructive">{error}</p>}

      <section aria-labelledby="h-scheduled" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="h-scheduled" className="text-xl font-semibold">Scheduled</h2>
          <ScheduleDialog defaultNode={defaultNode} onSaved={(list, name) => { setSchedules(list); setAnnounce(`${name} scheduled.`); }} />
        </div>
        <p className="text-sm text-muted-foreground">
          At start time the logger opens the net and links the node (monitor only), then closes it when the time is up.
          If a net is already open, the scheduled one is skipped.
        </p>
        {!schedules ? <p className="text-muted-foreground">Loading…</p> : schedules.length === 0 ? (
          <p className="rounded-xl border border-dashed px-4 py-8 text-center text-muted-foreground">No nets scheduled yet.</p>
        ) : (
          <ul className="grid gap-3 md:grid-cols-2">
            {schedules.map((s) => (
              <li key={s.id}>
                <Card className={`gap-3 py-4 ${s.enabled ? "" : "border-dashed"}`}>
                  <CardHeader className="px-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="leading-none font-semibold">{s.name}</h3>
                      {s.running_now && <Badge>Running now</Badge>}
                      {!s.enabled && <Badge variant="outline">Paused</Badge>}
                    </div>
                    <CardDescription>{s.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-3 px-4 text-sm">
                    <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
                      <dt className="text-muted-foreground">Next</dt>
                      <dd>{s.enabled && s.next_start ? when(s.next_start) : "Not scheduled"}</dd>
                      <dt className="text-muted-foreground">Node</dt>
                      <dd className="font-mono">{s.node || "None (stays as is)"}</dd>
                      <dt className="text-muted-foreground">Time zone</dt>
                      <dd>{s.tz.replace(/_/g, " ")}</dd>
                    </dl>
                    <div className="flex flex-wrap gap-2">
                      <ScheduleDialog schedule={s} defaultNode={defaultNode}
                        onSaved={(list) => { setSchedules(list); setAnnounce(`${s.name} updated.`); }} />
                      <Button variant="outline" size="sm" className="max-md:h-11" onClick={() => toggle(s)}
                        aria-label={`${s.enabled ? "Pause" : "Turn on"} ${s.name}`}>
                        {s.enabled ? "Pause" : "Turn on"}
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive max-md:h-11"
                            aria-label={`Delete ${s.name} schedule`}>Delete</Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent onCloseAutoFocus={(e) => { e.preventDefault(); heading.current?.focus(); }}>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete the {s.name} schedule?</AlertDialogTitle>
                            <AlertDialogDescription>Past nets and their logs stay.</AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Keep</AlertDialogCancel>
                            <AlertDialogAction variant="destructive" onClick={() => remove(s)}>Delete</AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </CardContent>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="h-past" className="flex flex-col gap-3">
        <h2 id="h-past" className="text-xl font-semibold">Past nets</h2>
        {!nets ? <p className="text-muted-foreground">Loading…</p> : nets.length === 0 ? (
          <p className="rounded-xl border border-dashed px-4 py-8 text-center text-muted-foreground">No nets logged yet.</p>
        ) : (
          <div className="rounded-xl border bg-card">
            <Table label="Past nets">
              <TableHeader>
                <TableRow>
                  <TableHead scope="col" className="pl-4">Net</TableHead>
                  <TableHead scope="col">Started</TableHead>
                  <TableHead scope="col">Length</TableHead>
                  <TableHead scope="col">Check-ins</TableHead>
                  <TableHead scope="col" className="pr-4"><span className="sr-only">Actions</span></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {nets.map((n) => (
                  <TableRow key={n.id}>
                    <TableCell className="pl-4">
                      <span className="font-medium">{n.name}</span>
                      {n.schedule_id && <span className="ml-2 text-xs text-muted-foreground">scheduled</span>}
                    </TableCell>
                    <TableCell>{when(n.opened)}</TableCell>
                    <TableCell>{n.closed ? length(n.opened, n.closed) : <Badge>Open now</Badge>}</TableCell>
                    <TableCell>{n.checkin_count}</TableCell>
                    <TableCell className="pr-4">
                      <div className="flex justify-end gap-1">
                        <Button asChild variant="outline" size="sm" className="max-md:h-11">
                          <a href={`#/nets/${n.id}`} aria-label={`View ${n.name}`}><FileText aria-hidden="true" />View</a>
                        </Button>
                        <Button asChild variant="ghost" size="sm" className="max-md:h-11">
                          <a href={`/api/export.csv?net=${n.id}`} aria-label={`Download CSV for ${n.name}`}><Download aria-hidden="true" />CSV</a>
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </section>
      <div aria-live="polite" className="sr-only">{announce}</div>
    </div>
  );
}

function ScheduleDialog({ schedule, defaultNode, onSaved }: {
  schedule?: Schedule; defaultNode: string; onSaved: (list: Schedule[], name: string) => void;
}) {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const blank = {
    name: "", repeat: "weekly" as Schedule["repeat"], weekday: 4, week_of_month: 1, date: "",
    start: "19:00", duration_min: 60, node: defaultNode, disconnect_after: true,
  };
  const fromSchedule = (s: Schedule) => ({
    name: s.name, repeat: s.repeat, weekday: s.weekday ?? 4, week_of_month: s.week_of_month ?? 1, date: s.date ?? "",
    start: s.start, duration_min: s.duration_min, node: s.node ?? "", disconnect_after: !!s.disconnect_after,
  });
  const [open, setOpen] = useState(false);
  const [f, setF] = useState(blank);
  const [error, setError] = useState("");
  const nameRef = useRef<HTMLInputElement>(null);
  const set = <K extends keyof typeof blank>(k: K, v: (typeof blank)[K]) => setF((x) => ({ ...x, [k]: v }));

  const save = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const body = { ...f, tz: schedule?.tz || tz, duration_min: Number(f.duration_min) };
      const r = await post<{ schedules: Schedule[] }>(schedule ? `/api/schedules/${schedule.id}` : "/api/schedules", body);
      setOpen(false);
      onSaved(r.schedules, f.name);
    } catch (err) {
      setError((err as Error).message);
      nameRef.current?.focus();
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { setF(schedule ? fromSchedule(schedule) : blank); setError(""); } }}>
      <DialogTrigger asChild>
        {schedule
          ? <Button variant="outline" size="sm" className="max-md:h-11" aria-label={`Edit ${schedule.name}`}>Edit</Button>
          : <Button className="max-md:h-11"><CalendarPlus aria-hidden="true" />Schedule a net</Button>}
      </DialogTrigger>
      <DialogContent className="max-h-[90svh] overflow-y-auto">
        <form onSubmit={save} noValidate className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>{schedule ? `Edit ${schedule.name}` : "Schedule a net"}</DialogTitle>
            <DialogDescription>Times are in {(schedule?.tz || tz).replace(/_/g, " ")}.</DialogDescription>
          </DialogHeader>
          <p id="sched-error" role="alert" className="text-sm font-medium text-destructive empty:hidden">{error}</p>
          <div className="flex flex-col gap-2">
            <Label htmlFor="s-name">Net name</Label>
            <Input ref={nameRef} id="s-name" value={f.name} onChange={(e) => set("name", e.target.value)}
              placeholder="Tuesday Night Net" aria-describedby="sched-error" />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="s-repeat">Repeats</Label>
            <NativeSelect id="s-repeat" value={f.repeat} onChange={(e) => set("repeat", e.target.value as Schedule["repeat"])}>
              <option value="weekly">Every week</option>
              <option value="monthly">Once a month</option>
              <option value="once">One time</option>
            </NativeSelect>
          </div>
          {f.repeat === "monthly" && (
            <div className="flex flex-col gap-2">
              <Label htmlFor="s-week">Which week</Label>
              <NativeSelect id="s-week" value={f.week_of_month} onChange={(e) => set("week_of_month", Number(e.target.value))}>
                {WEEKS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </NativeSelect>
            </div>
          )}
          {f.repeat !== "once" ? (
            <div className="flex flex-col gap-2">
              <Label htmlFor="s-day">Day</Label>
              <NativeSelect id="s-day" value={f.weekday} onChange={(e) => set("weekday", Number(e.target.value))}>
                {WEEKDAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}
              </NativeSelect>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <Label htmlFor="s-date">Date</Label>
              <Input id="s-date" type="date" value={f.date} onChange={(e) => set("date", e.target.value)} />
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-2">
              <Label htmlFor="s-start">Start time</Label>
              <Input id="s-start" type="time" value={f.start} onChange={(e) => set("start", e.target.value)} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="s-len">Length (minutes)</Label>
              <Input id="s-len" type="number" inputMode="numeric" min={5} max={480} step={5}
                value={f.duration_min} onChange={(e) => set("duration_min", Number(e.target.value))} />
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="s-node">Node to link</Label>
            <Input id="s-node" inputMode="numeric" value={f.node} onChange={(e) => set("node", e.target.value)}
              placeholder="Leave blank to not change links" className="font-mono" aria-describedby="s-node-hint" />
            <p id="s-node-hint" className="text-sm text-muted-foreground">Linked in monitor mode at start. The logger never transmits.</p>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={f.disconnect_after} onChange={(e) => set("disconnect_after", e.target.checked)}
                className="size-4 accent-primary" />
              Disconnect the node when the net ends
            </label>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit">{schedule ? "Save" : "Schedule"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
