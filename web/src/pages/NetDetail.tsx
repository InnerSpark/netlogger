import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Download, FileText } from "lucide-react";
import { get, type NetDetail as Detail } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { when } from "@/pages/Nets";

const FLAG_LABEL: Record<string, string> = { traffic: "Traffic", short_time: "Short time", recheck: "Recheck" };
const clock = (ts: number) => new Date(ts * 1000).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" });

export function NetDetail({ id }: { id: number }) {
  const [d, setD] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");

  useEffect(() => {
    get<Detail>(`/api/nets/${id}`).then(setD).catch((e) => setError((e as Error).message));
  }, [id]);

  const shown = useMemo(() => {
    if (!d) return [];
    const needle = q.trim().toLowerCase();
    return needle ? d.transmissions.filter((t) => `${t.text} ${t.calls || ""}`.toLowerCase().includes(needle)) : d.transmissions;
  }, [d, q]);

  if (error) return <p role="alert" className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-destructive">{error}</p>;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <a href="#/nets" className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground max-md:min-h-11">
          <ArrowLeft aria-hidden="true" className="size-4" />All nets
        </a>
        <h1 tabIndex={-1} className="text-2xl font-semibold tracking-tight outline-none">{d ? d.net.name : "Loading…"}</h1>
        {d && (
          <p className="text-muted-foreground">
            {when(d.net.opened)}
            {d.net.closed ? `, ${Math.max(1, Math.round((d.net.closed - d.net.opened) / 60))} minutes` : ""}
            {" · "}{d.checkins.length} check-ins · {d.transmissions.length} transmissions
            {!d.net.closed && <Badge className="ml-2">Open now</Badge>}
          </p>
        )}
        {d && (
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline" className="max-md:h-11">
              <a href={`/api/export.csv?net=${id}`}><Download aria-hidden="true" />Check-ins CSV</a>
            </Button>
            <Button asChild variant="outline" className="max-md:h-11">
              <a href={`/api/nets/${id}/transcript.txt`}><FileText aria-hidden="true" />Transcript</a>
            </Button>
          </div>
        )}
      </div>

      {d && (
        <>
          <section aria-labelledby="h-roster" className="flex flex-col gap-3">
            <h2 id="h-roster" className="text-xl font-semibold">Check-ins</h2>
            {d.checkins.length === 0 ? <p className="text-muted-foreground">No check-ins logged.</p> : (
              <div className="rounded-xl border bg-card">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead scope="col" className="pl-4 max-md:hidden">#</TableHead>
                      <TableHead scope="col">Call</TableHead>
                      <TableHead scope="col" className="max-md:hidden">Name</TableHead>
                      <TableHead scope="col" className="max-md:hidden">Location</TableHead>
                      <TableHead scope="col">Time</TableHead>
                      <TableHead scope="col" className="pr-4">Flags</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {d.checkins.map((c, i) => (
                      <TableRow key={c.id}>
                        <TableCell className="pl-4 text-muted-foreground max-md:hidden">{i + 1}</TableCell>
                        <TableCell className="max-md:pl-4">
                          <span className="font-mono font-semibold">{c.call}</span>
                          {(c.name || c.location) && (
                            <span className="block text-muted-foreground md:hidden">{[c.name, c.location].filter(Boolean).join(", ")}</span>
                          )}
                        </TableCell>
                        <TableCell className="max-md:hidden">{c.name}</TableCell>
                        <TableCell className="max-md:hidden">{c.location}</TableCell>
                        <TableCell>{clock(c.ts)}</TableCell>
                        <TableCell className="pr-4">
                          <span className="flex flex-wrap gap-1">
                            {(c.flags || "").split(",").filter(Boolean).map((f) => <Badge key={f} variant="secondary">{FLAG_LABEL[f] || f}</Badge>)}
                            {!!c.first_time && <Badge variant="outline">First time</Badge>}
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </section>

          <section aria-labelledby="h-transcript" className="flex flex-col gap-3">
            <h2 id="h-transcript" className="text-xl font-semibold">Transcript</h2>
            <div className="flex max-w-sm flex-col gap-2">
              <Label htmlFor="t-search">Search</Label>
              <Input id="t-search" type="search" value={q} onChange={(e) => setQ(e.target.value)}
                placeholder="Callsign or words" aria-describedby="t-count" className="max-md:h-11" />
              <p id="t-count" className="text-sm text-muted-foreground" aria-live="polite">
                {q.trim() ? `${shown.length} of ${d.transmissions.length} transmissions` : `${d.transmissions.length} transmissions`}
              </p>
            </div>
            {shown.length === 0 ? <p className="text-muted-foreground">Nothing to show.</p> : (
              <ol className="flex flex-col divide-y rounded-xl border bg-card px-4">
                {shown.map((t, i) => (
                  <li key={`${t.ts}-${i}`} className="flex flex-col gap-1 py-2 text-sm sm:flex-row sm:gap-3">
                    <span className="shrink-0 font-medium tabular-nums">{clock(t.ts)}</span>
                    <span className="flex-1">{t.text}</span>
                    {t.calls && <span className="shrink-0 font-mono text-muted-foreground">{t.calls.replace(/,/g, ", ")}</span>}
                  </li>
                ))}
              </ol>
            )}
          </section>
        </>
      )}
    </div>
  );
}
