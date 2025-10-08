import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date) {
  return new Date(date).toLocaleDateString("fr-FR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatNumber(num: number) {
  return new Intl.NumberFormat("fr-FR").format(num);
}

export function formatCurrency(amount: string) {
  // Extract number from string like "$394.3 billion"
  const match = amount.match(/[\d,.]+/);
  if (!match) return amount;

  const number = parseFloat(match[0].replace(",", ""));
  const unit = amount.replace(/[\d,.$\s]+/, "").trim();

  return `${formatNumber(number)} ${unit}`;
}

export function getConfidenceColor(score: number) {
  if (score >= 0.8) return "text-green-600 bg-green-100";
  if (score >= 0.6) return "text-yellow-600 bg-yellow-100";
  return "text-red-600 bg-red-100";
}

export function getConfidenceLabel(score: number) {
  if (score >= 0.8) return "Élevée";
  if (score >= 0.6) return "Moyenne";
  return "Faible";
}

export function debounce<T extends (...args: unknown[]) => void>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}
