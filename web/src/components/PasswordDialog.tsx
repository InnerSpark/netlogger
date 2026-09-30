import { useRef, useState, type FormEvent } from "react";
import { post } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function PasswordDialog() {
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const currentRef = useRef<HTMLInputElement>(null);
  const nextRef = useRef<HTMLInputElement>(null);

  const reset = (o: boolean) => {
    setOpen(o);
    if (o) { setCurrent(""); setNext(""); setError(""); setDone(false); }
  };

  const save = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await post("/api/me/password", { current, new: next });
      setDone(true);
      setError("");
    } catch (err) {
      const msg = (err as Error).message;
      setError(msg);
      (msg.startsWith("Current") ? currentRef : nextRef).current?.focus();
    }
  };

  return (
    <Dialog open={open} onOpenChange={reset}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="max-md:h-11">Change password</Button>
      </DialogTrigger>
      <DialogContent>
        {done ? (
          <>
            <DialogHeader>
              <DialogTitle>Password changed</DialogTitle>
              <DialogDescription>Other devices signed in to this account were logged out.</DialogDescription>
            </DialogHeader>
            <DialogFooter><Button onClick={() => setOpen(false)}>Done</Button></DialogFooter>
          </>
        ) : (
          <form onSubmit={save} noValidate className="flex flex-col gap-4">
            <DialogHeader>
              <DialogTitle>Change password</DialogTitle>
              <DialogDescription>At least 10 characters. Other devices get logged out.</DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-2">
              <Label htmlFor="pw-current">Current password</Label>
              <Input ref={currentRef} id="pw-current" type="password" autoComplete="current-password"
                value={current} onChange={(e) => setCurrent(e.target.value)} aria-describedby="pw-error"
                aria-invalid={error.startsWith("Current") || undefined} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="pw-new">New password</Label>
              <Input ref={nextRef} id="pw-new" type="password" autoComplete="new-password"
                value={next} onChange={(e) => setNext(e.target.value)} aria-describedby="pw-error"
                aria-invalid={(!!error && !error.startsWith("Current")) || undefined} />
            </div>
            <p id="pw-error" role="alert" className="min-h-5 text-sm font-medium text-destructive">{error}</p>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit">Change password</Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
