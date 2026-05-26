import { useEffect, useState } from "react";
import { useStore } from "../../store";

export function TopBar() {
  const selectedSatellite = useStore((s) => s.selectedSatellite);
  const sdrStatus = useStore((s) => s.sdrStatus);
  const spectrum = useStore((s) => s.spectrum);
  const wsConnected = useStore((s) => s.wsConnected);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  // Prefer the live WS spectrum frame (refreshes at ~10 Hz) over the
  // last-known REST status — surfaces drift caused by another client retuning.
  const actualFreqHz = spectrum?.center_frequency_hz ?? sdrStatus.frequency_hz;
  const tuneMismatch =
    selectedSatellite != null &&
    actualFreqHz != null &&
    actualFreqHz !== selectedSatellite.frequency_hz;

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-panel border-b border-panel-border">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-bold text-accent tracking-wider">SATOPS</h1>
        <span className="text-text-secondary">
          {selectedSatellite?.name ?? "No satellite selected"}
        </span>
        {tuneMismatch && actualFreqHz != null && selectedSatellite != null && (
          <span
            className="text-warning text-xs"
            title={`SDR tuned to ${(actualFreqHz / 1e6).toFixed(3)} MHz, but ${selectedSatellite.name} is at ${(selectedSatellite.frequency_hz / 1e6).toFixed(3)} MHz. Likely a setFrequency error or another client retuned the radio.`}
          >
            ⚠ SDR @ {(actualFreqHz / 1e6).toFixed(3)} MHz
          </span>
        )}
      </div>

      <div className="flex items-center gap-6 text-xs">
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              !sdrStatus.connected
                ? "bg-danger"
                : sdrStatus.mode === "synthetic"
                  ? "bg-warning"
                  : "bg-accent"
            }`}
          />
          <span
            className={
              sdrStatus.connected && sdrStatus.mode === "synthetic"
                ? "text-warning"
                : "text-text-secondary"
            }
          >
            SDR{" "}
            {!sdrStatus.connected
              ? "OFF"
              : sdrStatus.mode === "synthetic"
                ? "SYNTHETIC"
                : "ON"}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${wsConnected ? "bg-accent" : "bg-danger"}`}
          />
          <span className="text-text-secondary">WS</span>
        </div>

        <span className="text-text-primary tabular-nums">
          {time.toISOString().slice(0, 19)}Z
        </span>
      </div>
    </div>
  );
}
