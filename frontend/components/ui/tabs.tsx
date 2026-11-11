"use client";
import * as T from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";

export const Tabs = T.Root;
export const TabsContent = T.Content;
export function TabsList({ className, ...p }: T.TabsListProps) {
  return <T.List className={cn("flex gap-1 border-b border-line", className)} {...p} />;
}
export function TabsTrigger({ className, ...p }: T.TabsTriggerProps) {
  return <T.Trigger className={cn("-mb-px border-b-2 border-transparent px-3 py-2.5 text-sm font-medium text-slate hover:text-ink data-[state=active]:border-clinical data-[state=active]:text-navy", className)} {...p} />;
}
