import { useEffect, useState } from "react";
import { useStore } from "../../store";
import { api } from "../../services/api";
import type { Observation } from "../../types";

export function PassHistory() {
  const [observations, setObservations] = useState<Observation[]>([]);
  const activePass = useStore((s) => s.activePass);

  // Refresh observations periodically and when active pass changes
  useEffect(() => {
    api.getObservations().then(setObservations);
    const interval = setInterval(() => {
      api.getObservations().then(setObservations);
    }, 30_000);
    return () => clearInterval(interval);
  }, []);

  // Refresh when a pass might have ended (activePass goes null)
  useEffect(() => {
    if (!activePass) {
      api.getObservations().then(setObservations);
    }
  }, [activePass]);

  return (
    <div className="p-3 bg-panel rounded border border-panel-border">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xs font-bold text-text-secondary uppercase tracking-widest">
          Pass History
        </h2>
        {activePass && (
          <div className="flex items-center gap-2 text-xs">
            <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
            <span className="text-accent">
              ACTIVE: {activePass.satellite} — El {activePass.max_elevation}°
              {activePass.peak_signal != null && ` — Peak ${activePass.peak_signal} dB`}
            </span>
          </div>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-text-secondary border-b border-panel-border">
              <th className="text-left py-1 px-2">Start</th>
              <th className="text-left py-1 px-2">End</th>
              <th className="text-right py-1 px-2">Peak Signal</th>
              <th className="text-right py-1 px-2">Avg SNR</th>
              <th className="text-left py-1 px-2">Notes</th>
            </tr>
          </thead>
          <tbody>
            {observations.length === 0 && (
              <tr>
                <td colSpan={5} className="text-text-secondary py-4 text-center">
                  No observations recorded
                </td>
              </tr>
            )}
            {observations.map((obs) => (
              <tr key={obs.id} className="border-b border-panel-border hover:bg-surface">
                <td className="py-1 px-2 tabular-nums">
                  {new Date(obs.start_time).toLocaleString()}
                </td>
                <td className="py-1 px-2 tabular-nums">
                  {new Date(obs.end_time).toLocaleString()}
                </td>
                <td className="py-1 px-2 text-right tabular-nums">
                  {obs.peak_signal?.toFixed(1) ?? "—"} dBm
                </td>
                <td className="py-1 px-2 text-right tabular-nums">
                  {obs.avg_snr?.toFixed(1) ?? "—"} dB
                </td>
                <td className="py-1 px-2 text-text-secondary">{obs.notes ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
