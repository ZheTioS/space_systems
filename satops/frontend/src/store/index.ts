import { create } from "zustand";
import type {
  ActivePassUpdate,
  Satellite,
  SatellitePass,
  TrackingUpdate,
  SpectrumUpdate,
  LinkBudgetUpdate,
  SdrStatus,
} from "../types";

interface SatOpsState {
  // Satellites
  satellites: Satellite[];
  selectedSatellite: Satellite | null;
  setSatellites: (sats: Satellite[]) => void;
  selectSatellite: (sat: Satellite) => void;

  // Passes
  passes: SatellitePass[];
  setPasses: (passes: SatellitePass[]) => void;

  // Live tracking
  tracking: TrackingUpdate | null;
  setTracking: (update: TrackingUpdate) => void;

  // Spectrum
  spectrum: SpectrumUpdate | null;
  setSpectrum: (update: SpectrumUpdate) => void;

  // Link budget
  linkBudget: LinkBudgetUpdate | null;
  setLinkBudget: (update: LinkBudgetUpdate) => void;

  // Active pass
  activePass: ActivePassUpdate | null;
  setActivePass: (update: ActivePassUpdate | null) => void;

  // SDR
  sdrStatus: SdrStatus;
  setSdrStatus: (status: SdrStatus) => void;

  // Connection
  wsConnected: boolean;
  setWsConnected: (connected: boolean) => void;

  // Radio tuning scope — when "local", PassPanel must NOT auto-retune the SDR.
  radioTuning: "sat" | "local";
  setRadioTuning: (t: "sat" | "local") => void;
}

export const useStore = create<SatOpsState>((set) => ({
  satellites: [],
  selectedSatellite: null,
  setSatellites: (satellites) => set({ satellites }),
  selectSatellite: (sat) => set({ selectedSatellite: sat }),

  passes: [],
  setPasses: (passes) => set({ passes }),

  tracking: null,
  setTracking: (tracking) => set({ tracking }),

  spectrum: null,
  setSpectrum: (spectrum) => set({ spectrum }),

  linkBudget: null,
  setLinkBudget: (linkBudget) => set({ linkBudget }),

  activePass: null,
  setActivePass: (activePass) => set({ activePass }),

  sdrStatus: { connected: false, mode: "synthetic", driver: null, frequency_hz: null, sample_rate: null, gain: null },
  setSdrStatus: (sdrStatus) => set({ sdrStatus }),

  wsConnected: false,
  setWsConnected: (wsConnected) => set({ wsConnected }),

  radioTuning: "sat",
  setRadioTuning: (radioTuning) => set({ radioTuning }),
}));
