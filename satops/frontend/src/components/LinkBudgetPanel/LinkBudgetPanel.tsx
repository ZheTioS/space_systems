import { config } from "../../config";
import { useStore } from "../../store";

export function LinkBudgetPanel() {
  const linkBudget = useStore((s) => s.linkBudget);
  const tracking = useStore((s) => s.tracking);

  return (
    <div className="flex flex-col gap-3 p-3 bg-panel rounded border border-panel-border h-full">
      <h2 className="text-xs font-bold text-text-secondary uppercase tracking-widest">
        Link Budget
      </h2>

      {linkBudget ? (
        <div className="flex flex-col gap-2">
          <Metric label="FSPL" value={`${linkBudget.fspl_db.toFixed(1)} dB`} />
          <Metric label="Rx Power" value={`${linkBudget.received_power_dbm.toFixed(1)} dBm`} />
          <Metric label="Noise Power" value={`${linkBudget.noise_power_dbm.toFixed(1)} dBm`} />
          <Metric
            label="SNR"
            value={`${linkBudget.snr_db.toFixed(1)} dB`}
            highlight={linkBudget.snr_db > config.snrGoodDb}
            warning={linkBudget.snr_db < config.snrWarningDb}
          />
        </div>
      ) : (
        <span className="text-text-secondary text-xs">
          Waiting for satellite above horizon...
        </span>
      )}

      <h2 className="text-xs font-bold text-text-secondary uppercase tracking-widest mt-4">
        Signal Metrics
      </h2>

      {tracking ? (
        <div className="flex flex-col gap-2">
          <Metric label="Velocity" value={`${(tracking.velocity_km_s * 1000).toFixed(1)} m/s`} />
          <Metric label="Doppler" value={`${tracking.doppler_hz.toFixed(0)} Hz`} />
          <Metric label="Slant Range" value={`${tracking.range_km.toFixed(0)} km`} />
        </div>
      ) : (
        <span className="text-text-secondary text-xs">No tracking data</span>
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  highlight = false,
  warning = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  warning?: boolean;
}) {
  const valueColor = warning
    ? "text-danger"
    : highlight
      ? "text-accent"
      : "text-text-primary";

  return (
    <div className="flex justify-between items-center bg-surface rounded px-2 py-1.5">
      <span className="text-text-secondary text-xs">{label}</span>
      <span className={`text-xs tabular-nums font-medium ${valueColor}`}>{value}</span>
    </div>
  );
}
