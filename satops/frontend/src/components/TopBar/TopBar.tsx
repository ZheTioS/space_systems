import { useEffect, useState } from "react";
import { useStore } from "../../store";

export function TopBar() {
  const selectedSatellite = useStore((s) => s.selectedSatellite);
  const sdrStatus = useStore((s) => s.sdrStatus);
  const wsConnected = useStore((s) => s.wsConnected);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-panel border-b border-panel-border">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-bold text-accent tracking-wider">SATOPS</h1>
        <span className="text-text-secondary">
          {selectedSatellite?.name ?? "No satellite selected"}
        </span>
      </div>

      <div className="flex items-center gap-6 text-xs">
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${sdrStatus.connected ? "bg-accent" : "bg-danger"}`}
          />
          <span className="text-text-secondary">
            SDR {sdrStatus.connected ? "ON" : "OFF"}
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
