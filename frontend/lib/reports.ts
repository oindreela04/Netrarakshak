"use client";
import { toast } from "sonner";
import { blobUrl } from "./api";

export async function openReport(id: string, name: string, mode: "view" | "print" | "download" = "view") {
  try {
    const url = await blobUrl(`/reports/${id}/file${mode === "download" ? "?download=true" : ""}`);
    if (mode === "download") { const a = document.createElement("a"); a.href = url; a.download = `${name}.pdf`; a.click(); return; }
    const w = window.open(url, "_blank");
    if (mode === "print" && w) w.addEventListener("load", () => w.print());
  } catch (e: any) { toast.error(e.message); }
}
