export interface Satellite {
  id: number;
  name: string;
  norad_id: number;
  frequency_hz: number;
}

export interface SatellitePass {
  satellite_id: number;
  aos: string;
  los: string;
  max_elevation: number;
}

export interface TrackingUpdate {
  type: "tracking_update";
  timestamp: string;
  satellite: string;
  azimuth_deg: number;
  elevation_deg: number;
  range_km: number;
  velocity_km_s: number;
  doppler_hz: number;
  lat?: number;
  lon?: number;
}

export interface GroundTrack {
  current: { lat: number; lon: number; altitude_km: number };
  track: { lat: number; lon: number; time_offset_min: number }[];
  observer: { lat: number; lon: number };
}

export interface SpectrumUpdate {
  type: "spectrum_update";
  timestamp: string;
  center_frequency_hz: number;
  bandwidth_hz: number;
  magnitudes_db: number[];
}

export interface LinkBudgetUpdate {
  type: "link_budget";
  timestamp: string;
  fspl_db: number;
  received_power_dbm: number;
  noise_power_dbm: number;
  snr_db: number;
}

export interface SdrStatus {
  connected: boolean;
  mode: "hardware" | "synthetic";
  driver: string | null;
  frequency_hz: number | null;
  sample_rate: number | null;
  gain: number | null;
}

export interface Observation {
  id: number;
  pass_id: number;
  start_time: string;
  end_time: string;
  peak_signal: number | null;
  avg_snr: number | null;
  notes: string | null;
}

export interface ActivePassUpdate {
  type: "active_pass";
  timestamp: string;
  satellite: string;
  aos: string;
  max_elevation: number;
  peak_signal: number | null;
  samples: number;
}

export interface ActivePassClearedEvent {
  type: "active_pass_cleared";
  timestamp: string;
}

export type WsEvent =
  | TrackingUpdate
  | SpectrumUpdate
  | LinkBudgetUpdate
  | ActivePassUpdate
  | ActivePassClearedEvent;
