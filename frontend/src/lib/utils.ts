import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatAUD(value: number | string): string {
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (!isFinite(n)) return "—";
  return new Intl.NumberFormat("en-AU", {
    style: "currency",
    currency: "AUD",
    minimumFractionDigits: 2,
  }).format(n);
}

export function formatVolume(ml: number | null | undefined): string {
  if (ml == null) return "—";
  if (ml >= 1000) return `${(ml / 1000).toFixed(3).replace(/\.?0+$/, "")}L`.replace("L", " L");
  return `${ml} mL`;
}

export function retailerLabel(slug: string): string {
  switch (slug) {
    case "danmurphys":
      return "Dan Murphy's";
    case "bws":
      return "BWS";
    case "liquorland":
      return "Liquorland";
    default:
      return slug;
  }
}