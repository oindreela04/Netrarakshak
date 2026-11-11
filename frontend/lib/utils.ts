import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmtDate(iso?: string | null, withTime = false) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
    timeZone: "Asia/Kolkata",
  });
}

export function inr(n: number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);
}

export const pct = (n?: number | null) => (n == null ? "—" : `${(n * 100).toFixed(1)}%`);

export const GRADE_LABEL: Record<string, string> = {
  no_dr: "No apparent DR",
  mild_npdr: "Mild NPDR",
  moderate_npdr: "Moderate NPDR",
  severe_npdr: "Severe NPDR",
  proliferative_dr: "Proliferative DR",
  ungradable: "Ungradable",
  not_assessed: "Not assessed",
};

export const STATUS_LABEL: Record<string, string> = {
  draft: "Awaiting images",
  quality_checked: "Ready for analysis",
  analysed: "Awaiting review",
  in_review: "In review",
  recapture_requested: "Recapture requested",
  signed: "Signed",
  reported: "Reported",
};

export const ROLE_LABEL: Record<string, string> = {
  super_admin: "Platform administrator",
  hospital_admin: "Hospital administrator",
  ophthalmologist: "Ophthalmologist",
  technician: "Screening technician",
  receptionist: "Receptionist",
};
