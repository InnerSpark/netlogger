import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { Link2, Unplug } from "lucide-react";
import { get, post, type NodeState } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

// Link the logger's private node to any AllStar node, monitor only.
export function NodePanel({ admin }: { admin: boolean }) {
  const [s, setS] = useState<NodeState | null>(null);
  const [node, setNode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [announce, setAnnounce] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);

  const refresh = useCallback(async () => {
    try {
      setS(await get<NodeState>("/api/nodes"));
    } catch { /* dashboard shows the connection error */ }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [refresh]);

  const act = async (action: "connect" | "disconnect", n: string) => {
    setBusy(true);
    try {
      await post(`/api/nodes/${action}`, { node: n });
      setError("");
      setAnnounce(action === "connect" ? `Connecting to node ${n}.` : `Disconnected from node ${n}.`);
      if (action === "connect") setNode("");
      else heading.current?.focus(); // the row is gone
      // Links take a moment to come up; check again shortly
      await refresh();
      setTimeout(refresh, 1500);
    } catch (err) {
      setError((err as Error).message);
      if (action === "connect") input.current?.focus();
    } finally {
      setBusy(false);
    }
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const n = node.trim();
    if (!/^\d{3,7}$/.test(n)) {
      setError("Node numbers are 3 to 7 digits.");
      input.current?.focus();
      return;
    }
    act("connect", n);
  };

  return (
    <Card className="gap-4">
      <CardHeader>
        <CardTitle ref={heading} tabIndex={-1} className="outline-none">AllStar nodes</CardTitle>
        <CardDescription>
          {s?.enabled
            ? <>Logger node {s.logger_node} listens in monitor mode. It never transmits.</>
            : admin
              ? <>Node control is off. <a href="#/status" className="font-medium text-foreground underline underline-offset-4">See the setup guide, step 5</a>.</>
              : <>Node control is off. An admin can turn it on.</>}
        </CardDescription>
      </CardHeader>
      {s?.enabled && (
        <CardContent className="flex flex-col gap-4">
          {s.error ? (
            <p role="alert" className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">{s.error}</p>
          ) : s.links.length === 0 ? (
            <p className="text-sm text-muted-foreground">Not connected. Nothing is being logged from the air.</p>
          ) : (
            <ul aria-label="Connected nodes" className="flex flex-col divide-y rounded-md border">
              {s.links.map((l) => (
                <li key={l.node} className="flex items-center justify-between gap-3 px-3 py-2">
                  <span className="flex flex-col">
                    <span className="font-mono font-semibold">{l.node}</span>
                    <span className="text-xs text-muted-foreground">
                      {l.state === "ESTABLISHED" ? "Connected" : l.state.toLowerCase() || "connecting"}
                      {l.connected_for ? `, ${l.connected_for.split(":").slice(0, 3).join(":")}` : ""}
                    </span>
                  </span>
                  <Button variant="outline" size="sm" className="max-md:h-11" disabled={busy}
                    onClick={() => act("disconnect", l.node)} aria-label={`Disconnect node ${l.node}`}>
                    <Unplug aria-hidden="true" />Disconnect
                  </Button>
                </li>
              ))}
            </ul>
          )}
          <form onSubmit={submit} noValidate className="flex flex-col gap-2">
            <Label htmlFor="node">Connect to node</Label>
            <div className="flex gap-2 max-md:flex-col">
              <Input ref={input} id="node" inputMode="numeric" autoComplete="off" value={node}
                placeholder={s.default_node || "Node number"} onChange={(e) => setNode(e.target.value)}
                aria-invalid={!!error || undefined} aria-describedby="node-error" className="font-mono md:flex-1 max-md:h-11" />
              <Button type="submit" disabled={busy} className="max-md:h-11"><Link2 aria-hidden="true" />Connect</Button>
            </div>
            {s.default_node && !s.links.some((l) => l.node === s.default_node) && (
              <Button type="button" variant="link" className="h-auto self-start p-0" disabled={busy}
                onClick={() => act("connect", s.default_node)}>
                Connect to default node {s.default_node}
              </Button>
            )}
            <p id="node-error" role="alert" className="min-h-5 text-sm font-medium text-destructive">{error}</p>
          </form>
        </CardContent>
      )}
      <div aria-live="polite" className="sr-only">{announce}</div>
    </Card>
  );
}
