import type { Evidence } from "../types";

export function evidenceData<T>(value: unknown, fallback: T): T {
  if (!value || typeof value !== "object") return fallback;
  const candidate = value as Partial<Evidence<T>>;
  return candidate.data === undefined ? fallback : candidate.data;
}

export function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

export function arrayValue(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value)
    ? value.filter((item) => item && typeof item === "object") as Array<Record<string, unknown>>
    : [];
}

