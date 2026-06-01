import type { Satellite, SatellitePass, SdrStatus, Observation, GroundTrack } from "../types";

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

  getGroundTrack: (noradId: number) =>
    fetchJson<GroundTrack>(`/tracking/groundtrack/${noradId}`),

  refreshTles: () => fetchJson<{ loaded: number }>("/tracking/tle/refresh", { method: "POST" }),

  getSdrStatus: () => fetchJson<SdrStatus>("/sdr/status"),

  setFrequency: (frequencyHz: number) =>
    fetchJson<SdrStatus>(`/sdr/frequency?frequency_hz=${frequencyHz}`, { method: "POST" }),

  setAudioMode: (mode: "off" | "wfm" | "nfm") =>
    fetchJson<{ mode: string; audio_rate_hz: number }>(`/sdr/audio_mode?mode=${mode}`, { method: "POST" }),

  scanBand: (startHz?: number, endHz?: number, thresholdDb?: number) => {
    const params = new URLSearchParams();
    if (startHz != null) params.set("start_hz", String(startHz));
    if (endHz != null) params.set("end_hz", String(endHz));
    if (thresholdDb != null) params.set("threshold_db", String(thresholdDb));
    const qs = params.toString();
    return fetchJson<{
      start_hz: number;
      end_hz: number;
      threshold_db: number;
      stations: { frequency_hz: number; power_db: number; snr_db: number }[];
    }>(`/sdr/scan${qs ? `?${qs}` : ""}`, { method: "POST" });
  },

  getObservations: (limit = 50) => fetchJson<Observation[]>(`/observations/?limit=${limit}`),

  health: () => fetchJson<{ status: string; sdr: SdrStatus }>("/health"),
};
