import * as React from "react";
import { cn } from "@/lib/utils";

// Net Logger change: when a table is wider than the screen, its scroll box becomes a named,
// focusable region so keyboard users can scroll it (WCAG 2.1.1).
function Table({ className, label, ...props }: React.ComponentProps<"table"> & { label?: string }) {
  const box = React.useRef<HTMLDivElement>(null);
  const [scrolls, setScrolls] = React.useState(false);
  React.useEffect(() => {
    const el = box.current;
    if (!el) return;
    const check = () => setScrolls(el.scrollWidth > el.clientWidth + 1);
    check();
    const ro = new ResizeObserver(check);
    ro.observe(el);
    if (el.firstElementChild) ro.observe(el.firstElementChild);
    return () => ro.disconnect();
  }, []);
  return (
    <div ref={box} data-slot="table-container" className="relative w-full overflow-x-auto focus-visible:outline-2 focus-visible:outline-ring"
      {...(scrolls ? { tabIndex: 0, role: "region", "aria-label": label ? `${label}, scrolls sideways` : "Table, scrolls sideways" } : {})}>
      <table data-slot="table" className={cn("w-full caption-bottom text-sm", className)} {...props} />
    </div>
  );
}

function TableHeader({ className, ...props }: React.ComponentProps<"thead">) {
  return <thead data-slot="table-header" className={cn("[&_tr]:border-b", className)} {...props} />;
}

function TableBody({ className, ...props }: React.ComponentProps<"tbody">) {
  return <tbody data-slot="table-body" className={cn("[&_tr:last-child]:border-0", className)} {...props} />;
}

function TableRow({ className, ...props }: React.ComponentProps<"tr">) {
  return <tr data-slot="table-row" className={cn("hover:bg-muted/50 border-b transition-colors", className)} {...props} />;
}

function TableHead({ className, ...props }: React.ComponentProps<"th">) {
  return (
    <th
      data-slot="table-head"
      className={cn("text-foreground h-10 px-2 text-left align-middle font-medium whitespace-nowrap", className)}
      {...props}
    />
  );
}

function TableCell({ className, ...props }: React.ComponentProps<"td">) {
  return <td data-slot="table-cell" className={cn("p-2 align-middle whitespace-nowrap", className)} {...props} />;
}

export { Table, TableHeader, TableBody, TableHead, TableRow, TableCell };
