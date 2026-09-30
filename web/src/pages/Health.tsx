import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, ChevronDown, ChevronUp, CircleAlert, CircleDashed, Copy, ExternalLink, Loader2 } from "lucide-react";
import { get, type SetupState } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const DOCS = "https://github.com/InnerSpark/netlogger/blob/main/docs/allstar-setup.md";

type Status = "done" | "working" | "attention" | "todo";

const ago = (ts: number) => {
  const s = Math.max(0, Math.round(Date.now() / 1000 - ts));
  if (s < 60) return `${s} seconds ago`;
  if (s < 3600) return `${Math.round(s / 60)} minutes ago`;
  if (s < 86400) return `${Math.round(s / 3600)} hours ago`;
  return `${Math.round(s / 86400)} days ago`;
};

// The address this page was opened with is usually how the AllStar server can reach the logger too
function loggerAddress() {
  const h = window.location.hostname;
  return h === "localhost" || h === "127.0.0.1" ? "<this logger's IP>" : h;
}

export function Health() {
  const [s, setS] = useState<SetupState | null>(null);
  const [error, setError] = useState("");
  const [announce, setAnnounce] = useState("");
  // null = automatic: the guide opens itself while something needs fixing
  const [guideChoice, setGuideChoice] = useState<boolean | null>(null);

  const load = useCallback(async () => {
    try {
      setS(await get<SetupState>("/api/setup"));
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  // Same server as AllStar: everything talks over 127.0.0.1
  const ip = s?.same_host ? "127.0.0.1" : loggerAddress();
  const node = s?.logger_node || "1999";
  const port = s?.usrp_port || 34001;
  const testNode = s?.default_node || "2000";
  const amiHost = s?.ami_host || "<AllStar server IP>";

  const checks: { label: string; status: Status; detail: string; step?: number }[] = s ? [
    { label: "Net Logger is running", status: "done", detail: `Version ${s.version}.` },
    {
      label: "Speech to text",
      status: s.transcriber === "ready" ? "done" : "working",
      detail: s.transcriber === "ready"
        ? `Whisper ${s.whisper_model} is loaded.`
        : `Loading Whisper ${s.whisper_model}. The first start downloads the model, which can take a few minutes.`,
    },
    {
      label: "Audio from AllStar",
      status: s.last_packet ? "done" : "todo",
      detail: s.last_packet
        ? `Last audio ${ago(s.last_packet)}.`
        : `Nothing received on UDP ${port} yet. Do steps 1 to 4, then key up on a linked node.`,
      step: s.last_packet ? undefined : 1,
    },
    {
      label: "Node control",
      status: !s.node.configured ? "todo" : s.node.reachable ? "done" : "attention",
      detail: !s.node.configured
        ? "Off. Do step 5 to connect and disconnect nodes from the dashboard."
        : s.node.reachable
          ? `Talking to ${s.ami_host}:${s.ami_port} as ${s.ami_user}.`
          : s.node.error || "Can't reach the AllStar server.",
      step: s.node.configured && s.node.reachable ? undefined : 5,
    },
    {
      label: `Logger node ${node} linked`,
      status: s.node.links.length ? "done" : "todo",
      detail: s.node.links.length
        ? `Linked to ${s.node.links.map((l) => l.node).join(", ")}.`
        : "Not linked to any node. Connect one on the Dashboard or with the test command in step 4.",
    },
  ] : [];

  // Node control is optional, so only a broken one counts against health
  const healthy = !!s && s.transcriber === "ready" && !!s.last_packet && (!s.node.configured || !!s.node.reachable);
  const guideOpen = guideChoice ?? (!!s && !healthy);

  // Open the guide and move focus to a step's heading so screen readers announce it
  const goToStep = (n: number) => {
    setGuideChoice(true);
    requestAnimationFrame(() => {
      const el = document.getElementById(`step-${n}`);
      if (!el) return;
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
      el.focus({ preventScroll: true });
    });
  };

  const copied = (what: string) => setAnnounce(`${what} copied.`);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 tabIndex={-1} className="text-2xl font-semibold tracking-tight outline-none">Health</h1>
        <p className="text-muted-foreground">
          {!s ? "Checking the logger…" : healthy
            ? "Everything is working. This page updates on its own."
            : "Something needs attention. The setup guide below walks you through it."}
        </p>
      </div>

      {error && <p role="alert" className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}

      <Card className="gap-4">
        <CardHeader>
          <CardTitle>Checks</CardTitle>
        </CardHeader>
        <CardContent>
          {!s ? <p className="text-muted-foreground">Loading…</p> : (
            <ul className="flex flex-col divide-y">
              {checks.map((c) => (
                <li key={c.label} className="flex gap-3 py-3">
                  <StatusIcon status={c.status} />
                  <div className="flex flex-col gap-0.5">
                    <span className="font-medium">
                      {c.label}
                      <span className="sr-only">: {STATUS_TEXT[c.status]}.</span>
                    </span>
                    <span className="text-sm text-muted-foreground">{c.detail}</span>
                    {c.step && (
                      <a href={`#/health`} onClick={(e) => { e.preventDefault(); goToStep(c.step!); }}
                        className="inline-flex w-fit items-center text-sm font-medium underline underline-offset-4 max-md:min-h-11">
                        Go to step {c.step}<span className="sr-only"> of the setup guide</span>
                      </a>
                    )}
                  </div>
                  <span className="ml-auto shrink-0 text-sm text-muted-foreground" aria-hidden="true">{STATUS_TEXT[c.status]}</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <section aria-labelledby="h-steps" className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="h-steps" className="text-xl font-semibold">Setup guide</h2>
          <div className="flex flex-wrap items-center gap-4">
            <Button asChild variant="link" className="h-auto p-0 max-md:h-11">
              <a href={DOCS} target="_blank" rel="noreferrer">
                Full guide on GitHub<ExternalLink aria-hidden="true" /><span className="sr-only"> (opens in a new tab)</span>
              </a>
            </Button>
            <Button type="button" variant="outline" size="sm" className="max-md:h-11"
              aria-expanded={guideOpen} aria-controls="guide" onClick={() => setGuideChoice(!guideOpen)}>
              {guideOpen ? <ChevronUp aria-hidden="true" /> : <ChevronDown aria-hidden="true" />}
              {guideOpen ? "Hide guide" : "Show guide"}
            </Button>
          </div>
        </div>
        {guideOpen && (
        <div id="guide" className="flex flex-col gap-4">
        {s?.same_host && (
          <p className="rounded-md border bg-muted/50 px-3 py-2 text-sm">
            <strong>Installed with install.sh?</strong> Steps 1 to 5 are already done. If Audio from AllStar still says Not set up, restart Asterisk: <code className="font-mono">sudo systemctl restart asterisk</code>
          </p>
        )}
        <p className="text-sm text-muted-foreground">
          Steps 1 to 4 run on your AllStar server over SSH. Back up <code className="font-mono">/etc/asterisk</code> first.
          Written for ASL3; other builds use the same files.
        </p>

        <Step n={1} title="Give the AllStar server a way to reach this logger">
          <p>
            The server sends audio to this logger on <strong>UDP {port}</strong>. On the same network, use this logger's LAN IP.
            If the server is somewhere else (like a cloud node), install <strong>Tailscale</strong> on both and use this logger's Tailscale IP (it starts with 100).
          </p>
          {s?.same_host ? (
            <p className="text-muted-foreground">Net Logger runs on the AllStar server itself, so the steps below use <code className="font-mono">127.0.0.1</code>. Nothing else to set up here.</p>
          ) : (
            <p className="text-muted-foreground">Below, the logger's address is filled in as <code className="font-mono">{ip}</code>, the address you opened this page with. Change it if the server reaches the logger another way.</p>
          )}
        </Step>

        <Step n={2} title="Make sure the USRP channel is loaded">
          <p>Check it:</p>
          <Code label="USRP check command" onCopy={copied}>{`sudo asterisk -rx "module show like usrp"`}</Code>
          <p>If <code className="font-mono">chan_usrp.so</code> isn't running, add this to <code className="font-mono">/etc/asterisk/modules.conf</code> and restart Asterisk:</p>
          <Code label="modules.conf line" onCopy={copied}>{`load = chan_usrp.so`}</Code>
        </Step>

        <Step n={3} title={`Add the logger's private node (${node})`}>
          <p>Private nodes are under 2000 and aren't registered with AllStarLink. Add this to <code className="font-mono">/etc/asterisk/rpt.conf</code>:</p>
          <Code label="rpt.conf node stanza" onCopy={copied}>{`[${node}](node-main)
rxchannel = USRP/${ip}:${port}:32001
duplex = 0
telemdefault = 0`}</Code>
          <p>In the <code className="font-mono">[nodes]</code> section of the same file:</p>
          <Code label="nodes line" onCopy={copied}>{`${node} = radio@127.0.0.1/${node},NONE`}</Code>
          <p>Restart and check that {node} is listed:</p>
          <Code label="restart commands" onCopy={copied}>{`sudo systemctl restart asterisk
sudo asterisk -rx "rpt localnodes"`}</Code>
        </Step>

        <Step n={4} title="Test it by hand">
          <p>Open a net on the Dashboard, then link the logger node in monitor mode:</p>
          <Code label="test link commands" onCopy={copied}>{`sudo asterisk -rx "rpt cmd ${node} ilink 2 ${testNode}"
sudo asterisk -rx "rpt lstats ${node}"`}</Code>
          <p>Key up on node {testNode}. <strong>Audio from AllStar</strong> above should turn to Done, and the transmission shows under Last heard on the Dashboard.</p>
        </Step>

        <Step n={5} title="Turn on node control (optional)">
          <p>This lets the Dashboard connect and disconnect nodes. On the AllStar server, add a user to <code className="font-mono">/etc/asterisk/manager.conf</code>. Pick a long random secret:</p>
          <Code label="manager.conf user" onCopy={copied}>{`[${s?.ami_user || "netlogger"}]
secret = <long random secret>
deny = 0.0.0.0/0.0.0.0
permit = ${ip}/255.255.255.255
read = command
write = command`}</Code>
          <p>Make sure <code className="font-mono">[general]</code> in that file has <code className="font-mono">enabled = yes</code>, then reload:</p>
          <Code label="manager reload command" onCopy={copied}>{`sudo asterisk -rx "manager reload"`}</Code>
          <p>On the computer running Net Logger, set these in <code className="font-mono">{s?.same_host ? "/etc/netlogger/netlogger.env" : ".env"}</code>:</p>
          <Code label=".env settings" onCopy={copied}>{`AMI_HOST=${amiHost}
AMI_PORT=${s?.ami_port || 5038}
AMI_USER=${s?.ami_user || "netlogger"}
AMI_SECRET=<same secret>
LOGGER_NODE=${node}
DEFAULT_NODE=${s?.default_node || "<your node>"}`}</Code>
          <p>Then restart Net Logger:</p>
          <Code label="restart Net Logger command" onCopy={copied}>{s?.same_host ? `sudo systemctl restart netlogger` : `docker compose up -d`}</Code>
        </Step>

        <Step n={6} title="Connect from the Dashboard">
          <p>
            On the Dashboard, the <strong>AllStar nodes</strong> card now has a Connect box. Links are always monitor only:
            the logger hears the node and never transmits.
          </p>
        </Step>
        </div>
        )}
      </section>

      <div aria-live="polite" className="sr-only">{announce}</div>
    </div>
  );
}

const STATUS_TEXT: Record<Status, string> = {
  done: "Done",
  working: "Working",
  attention: "Needs attention",
  todo: "Not set up",
};

function StatusIcon({ status }: { status: Status }) {
  const cls = "mt-0.5 size-5 shrink-0";
  if (status === "done") return <CheckCircle2 aria-hidden="true" className={`${cls} text-primary`} />;
  if (status === "working") return <Loader2 aria-hidden="true" className={`${cls} animate-spin text-muted-foreground motion-reduce:animate-none`} />;
  if (status === "attention") return <CircleAlert aria-hidden="true" className={`${cls} text-destructive`} />;
  return <CircleDashed aria-hidden="true" className={`${cls} text-muted-foreground`} />;
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <Card className="gap-3">
      <CardHeader>
        <h3 id={`step-${n}`} tabIndex={-1} className="flex scroll-mt-4 items-baseline gap-2 font-semibold leading-snug outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm">
          <span className="text-muted-foreground">Step {n}.</span> {title}
        </h3>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 text-sm leading-relaxed">{children}</CardContent>
    </Card>
  );
}

function Code({ children, label, onCopy }: { children: string; label: string; onCopy: (label: string) => void }) {
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(children);
    } catch {
      // Clipboard API needs HTTPS or localhost. Fall back to a hidden textarea.
      const t = document.createElement("textarea");
      t.value = children;
      t.setAttribute("readonly", "");
      t.style.position = "fixed";
      t.style.opacity = "0";
      document.body.appendChild(t);
      t.select();
      document.execCommand("copy");
      t.remove();
    }
    onCopy(label);
  };

  return (
    <div className="relative">
      <pre tabIndex={0} aria-label={label}
        className="overflow-x-auto rounded-md border bg-muted px-3 py-2.5 pr-20 font-mono text-sm leading-relaxed">
        <code>{children}</code>
      </pre>
      <Button type="button" variant="outline" size="sm" onClick={copy} className="absolute top-1.5 right-1.5 max-md:h-11"
        aria-label={`Copy ${label}`}>
        <Copy aria-hidden="true" />Copy
      </Button>
    </div>
  );
}
