"use client";
import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, ...p }, ref) => (
  <input ref={ref} className={cn("h-10 w-full rounded-md border border-line bg-white px-3 text-sm placeholder:text-slate/70 focus:border-clinical focus:outline-none focus:ring-2 focus:ring-clinical/15 disabled:bg-mist", className)} {...p} />
));
Input.displayName = "Input";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...p }, ref) => (
  <textarea ref={ref} className={cn("min-h-[88px] w-full rounded-md border border-line bg-white px-3 py-2 text-sm placeholder:text-slate/70 focus:border-clinical focus:outline-none focus:ring-2 focus:ring-clinical/15", className)} {...p} />
));
Textarea.displayName = "Textarea";

export const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(({ className, children, ...p }, ref) => (
  <select ref={ref} className={cn("h-10 w-full rounded-md border border-line bg-white px-3 text-sm focus:border-clinical focus:outline-none focus:ring-2 focus:ring-clinical/15", className)} {...p}>{children}</select>
));
Select.displayName = "Select";

export function Label({ className, ...p }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn("mb-1.5 block text-[13px] font-medium text-ink", className)} {...p} />;
}

/** Label + control. The label is programmatically associated with its control (accessibility). */
export function Field({ label, hint, children, className }: { label: string; hint?: string; children: React.ReactNode; className?: string }) {
  const auto = React.useId();
  const hintId = `${auto}-hint`;
  let id = auto;
  let control = children;
  if (React.isValidElement<{ id?: string; "aria-describedby"?: string }>(children)) {
    id = children.props.id ?? auto;
    control = React.cloneElement(children, { id, ...(hint ? { "aria-describedby": hintId } : {}) });
  }
  return (
    <div className={className}>
      <Label htmlFor={id}>{label}</Label>
      {control}
      {hint && <p id={hintId} className="mt-1 text-xs text-slate">{hint}</p>}
    </div>
  );
}

export function Check({ label, checked, onChange, disabled }: { label: React.ReactNode; checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <label className="flex cursor-pointer items-start gap-2.5 text-sm">
      <input type="checkbox" className="mt-0.5 h-4 w-4 accent-[#1F6FB2]" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      <span>{label}</span>
    </label>
  );
}
