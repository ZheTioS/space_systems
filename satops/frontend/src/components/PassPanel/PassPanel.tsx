import { useEffect } from "react";
import { config } from "../../config";
import { useStore } from "../../store";
import { api } from "../../services/api";

export function PassPanel() {
  const satellites = useStore((s) => s.satellites);
  const selectedSatellite = useStore((s) => s.selectedSatellite);
  const passes = useStore((s) => s.passes);
  const tracking = useStore((s) => s.tracking);
  const setSatellites = useStore((s) => s.setSatellites);
  const selectSatellite = useStore((s) => s.selectSatellite);
  const setPasses = useStore((s) => s.setPasses);

  useEffect(() => {
    api.getSatellites().then(setSatellites);
  }, [setSatellites]);

  useEffect(() => {
    if (selectedSatellite) {
      api.getPasses(selectedSatellite.norad_id).then(setPasses);
    }
  }, [selectedSatellite, setPasses]);

  // Auto-select first satellite
  useEffect(() => {
    if (satellites.length > 0 && !selectedSatellite) {
      selectSatellite(satellites[0]);
    }
  }, [satellites, selectedSatellite, selectSatellite]);

  return (
    <div className="flex flex-col gap-3 p-3 bg-panel rounded border border-panel-border h-full overflow-y-auto">
      <h2 className="text-xs font-bold text-text-secondary uppercase tracking-widest">
        Satellites
      </h2>

      <div className="flex flex-col gap-1">
        {satellites.map((sat) => (
          <button
            key={sat.id}
            onClick={() => selectSatellite(sat)}
            className={`text-left px-2 py-1.5 rounded text-xs transition-colors ${
              selectedSatellite?.id === sat.id
                ? "bg-accent/20 text-accent"
                : "text-text-primary hover:bg-panel-border"
            }`}
          >
            {sat.name}
            <span className="text-text-secondary ml-2">
              {(sat.frequency_hz / 1e6).toFixed(3)} MHz
            </span>
          </button>
        ))}
      </div>

      {tracking && (
        <>
          <h2 className="text-xs font-bold text-text-secondary uppercase tracking-widest mt-4">
            Position
          </h2>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <Metric label="AZ" value={`${tracking.azimuth_deg.toFixed(1)}°`} />
            <Metric label="EL" value={`${tracking.elevation_deg.toFixed(1)}°`} />
            <Metric label="Range" value={`${tracking.range_km.toFixed(0)} km`} />
            <Metric label="Doppler" value={`${tracking.doppler_hz.toFixed(0)} Hz`} />
          </div>
        </>
      )}

      <h2 className="text-xs font-bold text-text-secondary uppercase tracking-widest mt-4">
        Upcoming Passes
      </h2>
      <div className="flex flex-col gap-1">
        {passes.length === 0 && (
          <span className="text-text-secondary text-xs">No passes found</span>
        )}
        {passes.slice(0, config.maxUpcomingPasses).map((p, i) => (
          <div key={i} className="text-xs text-text-primary py-1 border-b border-panel-border">
            <div>
              AOS {new Date(p.aos).toLocaleTimeString()} — LOS{" "}
              {new Date(p.los).toLocaleTimeString()}
            </div>
            <div className="text-text-secondary">
              Max El: {p.max_elevation.toFixed(1)}°
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-surface rounded px-2 py-1">
      <div className="text-text-secondary text-[10px]">{label}</div>
      <div className="text-text-primary tabular-nums">{value}</div>
    </div>
  );
}
