import type { Satellite, SatellitePass, SdrStatus, Observation } from "../types";

const BASE = "/api";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  getSatellites: () => fetchJson<Satellite[]>("/tracking/satellites"),

  getPasses: (noradId: number, hours = 24) =>
    fetchJson<SatellitePass[]>(`/tracking/passes/${noradId}?hours=${hours}`),

  getPosition: (noradId: number) =>
    fetchJson<Record<string, number>>(`/tracking/position/${noradId}`),

  refreshTles: () => fetchJson<{ loaded: number }>("/tracking/tle/refresh", { method: "POST" }),

  getSdrStatus: () => fetchJson<SdrStatus>("/sdr/status"),

  setFrequency: (frequencyHz: number) =>
    fetchJson<SdrStatus>(`/sdr/frequency?frequency_hz=${frequencyHz}`, { method: "POST" }),

  getObservations: (limit = 50) => fetchJson<Observation[]>(`/observations/?limit=${limit}`),

  health: () => fetchJson<{ status: string; sdr: SdrStatus }>("/health"),
};
