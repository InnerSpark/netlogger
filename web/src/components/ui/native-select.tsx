import * as React from "react";
import { ChevronDownIcon } from "lucide-react";
import { cn } from "@/lib/utils";

function NativeSelect({ className, ...props }: React.ComponentProps<"select">) {
  return (
    <div className="relative w-full">
      <select
        data-slot="native-select"
        className={cn(
          "border-input dark:bg-input/30 h-9 w-full min-w-0 appearance-none rounded-md border bg-transparent pl-3 pr-9 py-1 text-base shadow-xs outline-none md:text-sm",
          "focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] disabled:opacity-50",
          className,
        )}
        {...props}
      />
      <ChevronDownIcon aria-hidden="true" className="text-muted-foreground pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2" />
    </div>
  );
}

export { NativeSelect };
