"use client";
import * as D from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export function Dialog({ open, onOpenChange, title, description, children, wide }: {
  open: boolean; onOpenChange: (o: boolean) => void; title: string; description?: string; children: React.ReactNode; wide?: boolean;
}) {
  return (
    <D.Root open={open} onOpenChange={onOpenChange}>
      <D.Portal>
        <D.Overlay className="fixed inset-0 z-40 bg-navy-900/45" />
        <D.Content className={cn("fixed left-1/2 top-1/2 z-50 max-h-[90vh] w-[calc(100%-32px)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg bg-white p-6 shadow-2xl", wide ? "max-w-3xl" : "max-w-lg")}>
          <D.Title className="text-lg font-semibold text-navy">{title}</D.Title>
          {description && <D.Description className="mt-1 text-sm text-slate">{description}</D.Description>}
          <div className="mt-5">{children}</div>
          <D.Close className="absolute right-4 top-4 rounded p-1 text-slate hover:bg-mist" aria-label="Close"><X className="h-4 w-4" /></D.Close>
        </D.Content>
      </D.Portal>
    </D.Root>
  );
}
