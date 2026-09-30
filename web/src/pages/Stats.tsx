import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { ChevronDown, ChevronUp, TrendingDown, TrendingUp } from "lucide-react";
import { get, type StatNet, type Stats as StatsData } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const RANGES = [
  { days: 90, label: "Last 3 months", prev: "the 3 months before" },
  { days: 180, label: "Last 6 months", prev: "the 6 months before" },
  { days: 365, label: "Last 12 months", prev: "the 12 months before" },
  { days: 0, label: "All time", prev: "" },
];

const day = (ts: number) => new Date(ts * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric" });
const fullDay = (ts: number) => new Date(ts * 1000).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric" });
const fmt = (n: number | null) => (n === null ? "–" : Number.isInteger(n) ? String(n) : n.toFixed(1));

export function Stats() {
  const [days, setDays] = useState(90);
  const [schedule, setSchedule] = useState("");
  const [data, setData] = useState<StatsData | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setData(await get<StatsData>(`/api/stats?days=${days}${schedule ? `&schedule=${schedule}` : ""}`));
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  }, [days, schedule]);

  useEffect(() => { load(); }, [load]);

  const range = RANGES.find((r) => r.days === days)!;
  const s = data?.summary;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 tabIndex={-1} className="text-2xl font-semibold tracking-tight outline-none">Stats</h1>
        <p className="text-muted-foreground">How your nets are doing over time.</p>
      </div>

      <div className="flex flex-wrap gap-4">
        <div className="flex w-full flex-col gap-1.5 sm:w-48">
          <Label htmlFor="st-range">Time range</Label>
          <NativeSelect id="st-range" value={days} onChange={(e) => setDays(Number(e.target.value))} className="max-md:h-11">
            {RANGES.map((r) => <option key={r.days} value={r.days}>{r.label}</option>)}
          </NativeSelect>
        </div>
        <div className="flex w-full flex-col gap-1.5 sm:w-56">
          <Label htmlFor="st-net">Net</Label>
          <NativeSelect id="st-net" value={schedule} onChange={(e) => setSchedule(e.target.value)} className="max-md:h-11">
            <option value="">All nets</option>
            {data?.schedules.map((sc) => <option key={sc.id} value={sc.id}>{sc.name}</option>)}
          </NativeSelect>
        </div>
      </div>

      <p aria-live="polite" className="sr-only">
        {data ? `Showing ${data.nets.length} ${data.nets.length === 1 ? "net" : "nets"}, ${range.label.toLowerCase()}.` : ""}
      </p>

      {error && <p role="alert" className="rounded-md border border-destructive/50 bg-background px-3 py-2 text-sm text-destructive">{error}</p>}

      {!data ? <p className="text-muted-foreground">Loading…</p> : data.nets.length === 0 ? (
        <Card>
          <CardContent>
            <p className="text-muted-foreground">
              No nets in this range yet. Stats fill in as you run nets. Try <strong>All time</strong> or another net.
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <section aria-label="Summary" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Tile label="Nets held" value={fmt(s!.nets)} />
            <Tile label="Typical check-ins" value={fmt(s!.median_checkins)}
              note={<Change now={s!.median_checkins} before={s!.prev_median_checkins} period={range.prev} />} />
            <Tile label="Stations heard" value={fmt(s!.stations)} note="Different calls" />
            <Tile label="First-timers" value={fmt(s!.first_timers)} note="Never logged before" />
          </section>

          <CheckinsChart nets={data.nets} />
          <Regulars data={data} />
        </>
      )}
    </div>
  );
}

function Tile({ label, value, note }: { label: string; value: string; note?: React.ReactNode }) {
  return (
    <Card className="gap-1 py-4">
      <CardContent className="flex flex-col gap-1 px-4">
        <span className="text-sm text-muted-foreground">{label}</span>
        <span className="text-3xl font-semibold tabular-nums">{value}</span>
        {note && <span className="text-sm text-muted-foreground">{note}</span>}
      </CardContent>
    </Card>
  );
}

function Change({ now, before, period }: { now: number | null; before: number | null; period: string }) {
  if (!period) return <>Half your nets had more, half had fewer</>;
  if (now === null || before === null) return <>Nothing to compare with yet</>;
  const diff = now - before;
  if (diff === 0) return <>Same as {period}</>;
  const Icon = diff > 0 ? TrendingUp : TrendingDown;
  return (
    <span className="inline-flex items-center gap-1">
      <Icon aria-hidden="true" className="size-4" />
      {diff > 0 ? "Up" : "Down"} {fmt(Math.abs(diff))} from {period} ({fmt(before)})
    </span>
  );
}

// ---------- check-ins per net: stacked bars, returning + first-time ----------
const H = 240;
const PAD = { top: 16, right: 12, bottom: 28, left: 32 };

function niceMax(v: number) {
  if (v <= 5) return 5;
  const step = Math.pow(10, Math.floor(Math.log10(v)));
  for (const m of [1, 2, 2.5, 5, 10]) if (m * step >= v) return m * step;
  return 10 * step;
}

// A bar segment with only its top corners rounded
function topRounded(x: number, y: number, w: number, h: number, r: number) {
  r = Math.min(r, w / 2, h);
  return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
}

function CheckinsChart({ nets }: { nets: StatNet[] }) {
  const wrap = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(600);
  const [hover, setHover] = useState<number | null>(null);
  const [table, setTable] = useState(false);

  useLayoutEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(280, Math.floor(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const max = niceMax(Math.max(...nets.map((n) => n.checkins), 1));
  const ticks = [0, max / 4, max / 2, (3 * max) / 4, max].filter((t) => Number.isInteger(t));
  const plotW = w - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;
  const band = plotW / nets.length;
  const barW = Math.max(3, Math.min(32, band * 0.6));
  const y = (v: number) => PAD.top + plotH - (v / max) * plotH;
  const labelEvery = Math.ceil(nets.length / Math.max(1, Math.floor(plotW / 64)));
  const peak = nets.reduce((a, b) => (b.checkins > a.checkins ? b : a));
  const last = nets[nets.length - 1];
  const summary = `Bar chart of check-ins for ${nets.length} nets from ${fullDay(nets[0].opened)} to ${fullDay(last.opened)}. ` +
    `Most was ${peak.checkins} on ${fullDay(peak.opened)}. Latest was ${last.checkins}. Use Show table for every value.`;
  const h = hover === null ? null : nets[hover];

  return (
    <Card className="gap-4">
      <CardHeader className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex flex-col gap-1.5">
          <CardTitle><h2>Check-ins per net</h2></CardTitle>
          <CardDescription>Each bar is one net.</CardDescription>
        </div>
        <Button type="button" variant="outline" size="sm" className="max-md:h-11" aria-expanded={table}
          aria-controls="checkins-table" onClick={() => setTable(!table)}>
          {table ? <ChevronUp aria-hidden="true" /> : <ChevronDown aria-hidden="true" />}
          {table ? "Hide table" : "Show table"}
        </Button>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm" aria-label="Legend">
          <li className="flex items-center gap-1.5"><span aria-hidden="true" className="size-3 rounded-sm bg-[var(--series-1)]" />Returning</li>
          <li className="flex items-center gap-1.5"><span aria-hidden="true" className="size-3 rounded-sm bg-[var(--series-2)]" />First time</li>
        </ul>
        <div ref={wrap} className="relative w-full" onMouseLeave={() => setHover(null)}>
          <svg width={w} height={H} role="img" aria-label={summary} className="block max-w-full overflow-visible">
            {ticks.map((t) => (
              <g key={t}>
                <line x1={PAD.left} x2={w - PAD.right} y1={y(t)} y2={y(t)} stroke="var(--border)" strokeWidth={1} />
                <text x={PAD.left - 8} y={y(t)} dy="0.32em" textAnchor="end" className="fill-muted-foreground text-xs tabular-nums">{t}</text>
              </g>
            ))}
            {nets.map((n, i) => {
              const cx = PAD.left + band * i + band / 2;
              const x = cx - barW / 2;
              const ret = n.checkins - n.first_timers;
              const gap = ret > 0 && n.first_timers > 0 ? 2 : 0;
              const retTop = y(ret);
              const ftTop = y(n.checkins);
              const faded = hover !== null && hover !== i;
              return (
                <g key={n.id} opacity={faded ? 0.45 : 1}>
                  {ret > 0 && (n.first_timers > 0
                    ? <rect x={x} y={retTop} width={barW} height={y(0) - retTop} fill="var(--series-1)" />
                    : <path d={topRounded(x, retTop, barW, y(0) - retTop, 4)} fill="var(--series-1)" />)}
                  {n.first_timers > 0 && (
                    <path d={topRounded(x, ftTop, barW, Math.max(0, retTop - ftTop - gap), 4)} fill="var(--series-2)" />
                  )}
                  {i % labelEvery === 0 && (
                    <text x={cx} y={H - 8} textAnchor="middle" className="fill-muted-foreground text-xs">{day(n.opened)}</text>
                  )}
                  {/* hit target is the whole column, wider than the bar */}
                  <rect x={PAD.left + band * i} y={PAD.top} width={band} height={plotH} fill="transparent"
                    onMouseEnter={() => setHover(i)} />
                </g>
              );
            })}
            {/* label only the latest bar */}
            <text x={PAD.left + band * (nets.length - 1) + band / 2} y={y(last.checkins) - 6} textAnchor="middle"
              className="fill-foreground text-xs font-medium tabular-nums" aria-hidden="true">{last.checkins}</text>
            <line x1={PAD.left} x2={w - PAD.right} y1={y(0)} y2={y(0)} stroke="var(--muted-foreground)" strokeWidth={1} />
          </svg>
          {h && hover !== null && (
            <div aria-hidden="true"
              className="pointer-events-none absolute z-10 w-52 rounded-md border bg-popover p-3 text-sm text-popover-foreground shadow-md"
              style={{
                left: Math.min(Math.max(0, PAD.left + band * hover + band / 2 - 104), w - 208),
                top: Math.max(0, y(h.checkins) - 128),
              }}>
              <p className="font-medium">{fullDay(h.opened)}</p>
              <p className="mb-2 truncate text-muted-foreground">{h.name}</p>
              <dl className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-0.5 tabular-nums">
                <dt className="flex items-center gap-1.5"><span className="size-2.5 rounded-sm bg-[var(--series-1)]" />Returning</dt><dd>{h.checkins - h.first_timers}</dd>
                <dt className="flex items-center gap-1.5"><span className="size-2.5 rounded-sm bg-[var(--series-2)]" />First time</dt><dd>{h.first_timers}</dd>
                <dt>Total</dt><dd className="font-medium">{h.checkins}</dd>
                <dt className="text-muted-foreground">Length</dt><dd className="text-muted-foreground">{h.minutes} min</dd>
              </dl>
            </div>
          )}
        </div>

        {table && (
          <div id="checkins-table" className="rounded-xl border">
            <Table label="Check-ins per net">
              <TableHeader>
                <TableRow>
                  <TableHead scope="col" className="pl-4">Date</TableHead>
                  <TableHead scope="col" className="max-md:hidden">Net</TableHead>
                  <TableHead scope="col" className="text-right">Check-ins</TableHead>
                  <TableHead scope="col" className="text-right">First time</TableHead>
                  <TableHead scope="col" className="text-right max-md:hidden">Traffic</TableHead>
                  <TableHead scope="col" className="pr-4 text-right">Length</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {[...nets].reverse().map((n) => (
                  <TableRow key={n.id}>
                    <TableCell className="pl-4"><a href={`#/nets/${n.id}`} className="underline underline-offset-4">{day(n.opened)}</a></TableCell>
                    <TableCell className="max-md:hidden">{n.name}</TableCell>
                    <TableCell className="text-right tabular-nums">{n.checkins}</TableCell>
                    <TableCell className="text-right tabular-nums">{n.first_timers}</TableCell>
                    <TableCell className="text-right tabular-nums max-md:hidden">{n.traffic}</TableCell>
                    <TableCell className="pr-4 text-right tabular-nums">{n.minutes} min</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Regulars({ data }: { data: StatsData }) {
  const total = data.nets.length;
  return (
    <Card className="gap-4">
      <CardHeader>
        <CardTitle><h2>Regulars</h2></CardTitle>
        <CardDescription>Stations that checked in most in this range.</CardDescription>
      </CardHeader>
      <CardContent className="px-0">
        <Table label="Regulars">
          <TableHeader>
            <TableRow>
              <TableHead scope="col" className="pl-6">Call</TableHead>
              <TableHead scope="col" className="max-md:hidden">Name</TableHead>
              <TableHead scope="col" className="text-right">Nets</TableHead>
              <TableHead scope="col" className="pr-6 text-right max-md:hidden">Last checked in</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.regulars.map((r) => (
              <TableRow key={r.call}>
                <TableCell className="pl-6 font-mono font-semibold">{r.call}</TableCell>
                <TableCell className="max-md:hidden">{r.name}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {r.nets} of {total}
                  <span className="ml-2 text-muted-foreground">({Math.round((r.nets / total) * 100)}%)</span>
                </TableCell>
                <TableCell className="pr-6 text-right max-md:hidden">{day(r.last)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
