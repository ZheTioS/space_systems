import { useEffect, useRef, useState } from "react";
import { config } from "../../config";
import { useStore } from "../../store";
import { api } from "../../services/api";

type DemodMode = "off" | "wfm" | "nfm";
type Tuning = "sat" | "local";

export function RadioPanel() {
  const sdrStatus = useStore((s) => s.sdrStatus);
  const selectedSatellite = useStore((s) => s.selectedSatellite);
  const setSdrStatus = useStore((s) => s.setSdrStatus);
  const tuning = useStore((s) => s.radioTuning);
  const setTuning = useStore((s) => s.setRadioTuning);

  const [mode, setMode] = useState<DemodMode>("off");
  const [playing, setPlaying] = useState(false);
  const [volume, setVolume] = useState(0.5);
  const [bufferedMs, setBufferedMs] = useState(0);
  const [localMhz, setLocalMhz] = useState("100.000");
  const [scanning, setScanning] = useState(false);
  const [stations, setStations] = useState<
    { frequency_hz: number; power_db: number; snr_db: number }[] | null
  >(null);
  const [scanError, setScanError] = useState<string | null>(null);

  const audioCtxRef = useRef<AudioContext | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const nextStartRef = useRef(0);
  const sampleRateRef = useRef(32000);

  useEffect(() => {
    if (gainNodeRef.current) gainNodeRef.current.gain.value = volume;
  }, [volume]);

  const stop = () => {
    wsRef.current?.close();
    wsRef.current = null;
    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(() => {});
      audioCtxRef.current = null;
      gainNodeRef.current = null;
    }
    setPlaying(false);
    setBufferedMs(0);
    api.setAudioMode("off").catch(() => {});
  };

  const start = async (m: DemodMode) => {
    if (m === "off") {
      stop();
      return;
    }
    await api.setAudioMode(m);

    const ctx = new AudioContext();
    const gain = ctx.createGain();
    gain.gain.value = volume;
    gain.connect(ctx.destination);
    audioCtxRef.current = ctx;
    gainNodeRef.current = gain;
    nextStartRef.current = ctx.currentTime + 0.1;  // ~100 ms pre-buffer

    const ws = new WebSocket(config.audioWsUrl);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onmessage = (ev) => {
      if (typeof ev.data === "string") {
        try {
          const header = JSON.parse(ev.data);
          if (header?.type === "audio_header" && header.sample_rate) {
            sampleRateRef.current = header.sample_rate;
          }
        } catch {
          // ignore
        }
        return;
      }
      const ctxNow = audioCtxRef.current;
      const gainNode = gainNodeRef.current;
      if (!ctxNow || !gainNode) return;

      const samples = new Float32Array(ev.data);
      if (samples.length === 0) return;
      const sampleRate = sampleRateRef.current;
      const buffer = ctxNow.createBuffer(1, samples.length, sampleRate);
      buffer.copyToChannel(samples, 0);

      const source = ctxNow.createBufferSource();
      source.buffer = buffer;
      source.connect(gainNode);

      let startAt = nextStartRef.current;
      const now = ctxNow.currentTime;
      if (startAt < now) startAt = now;
      if (startAt - now > 0.5) startAt = now + 0.05;  // drop jitter buildup
      source.start(startAt);
      nextStartRef.current = startAt + buffer.duration;
      setBufferedMs(Math.round((nextStartRef.current - now) * 1000));
    };

    ws.onclose = () => {
      if (audioCtxRef.current === ctx) {
        ctx.close().catch(() => {});
        audioCtxRef.current = null;
        gainNodeRef.current = null;
        setPlaying(false);
      }
    };

    setPlaying(true);
  };

  useEffect(() => () => stop(), []);

  const onModeChange = (m: DemodMode) => {
    setMode(m);
    if (m === "off") {
      stop();
    } else if (playing) {
      // Switch demod mode while playing: tell the backend, no need to restart WS.
      api.setAudioMode(m).catch(() => {});
    }
  };

  const onPlay = () => {
    if (playing) stop();
    else if (mode !== "off") start(mode);
  };

  const applyLocalFrequency = async () => {
    const mhz = Number(localMhz);
    if (!Number.isFinite(mhz) || mhz < 24 || mhz > 1766) {
      // R820T tuner range is 24-1766 MHz; reject anything outside it.
      return;
    }
    try {
      const status = await api.setFrequency(Math.round(mhz * 1e6));
      setSdrStatus(status);
    } catch {
      // Backend rejected the tune; UI will reflect the unchanged status next frame.
    }
  };

  const runScan = async () => {
    setScanning(true);
    setScanError(null);
    try {
      const result = await api.scanBand();
      setStations(result.stations);
      if (result.stations.length === 0) {
        setScanError("No stations above threshold — check antenna or lower threshold.");
      }
    } catch (err) {
      setScanError(err instanceof Error ? err.message : "Scan failed");
      setStations(null);
    } finally {
      setScanning(false);
    }
  };

  const tuneToStation = async (freqHz: number) => {
    setLocalMhz((freqHz / 1e6).toFixed(3));
    // Pick LOCAL automatically so PassPanel doesn't immediately retune away.
    if (tuning !== "local") setTuning("local");
    try {
      const status = await api.setFrequency(freqHz);
      setSdrStatus(status);
    } catch {
      // ignore — UI will sync via next status fetch
    }
  };

  const actualMhz = sdrStatus.frequency_hz != null ? sdrStatus.frequency_hz / 1e6 : null;

  return (
    <div className="flex flex-col gap-2 p-3 bg-panel rounded border border-panel-border">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-bold text-text-secondary uppercase tracking-widest">Radio</h2>
        {playing && (
          <span className="text-[10px] text-text-secondary tabular-nums">
            buf {bufferedMs}ms
          </span>
        )}
      </div>

      <div className="flex gap-1 text-xs">
        {(["sat", "local"] as Tuning[]).map((t) => (
          <button
            key={t}
            onClick={() => {
              setTuning(t);
              // Switching back to SAT: re-pin the radio to the selected
              // satellite (PassPanel's tune effect ignores changes while
              // tuning === "local", so this puts the radio back in sync).
              if (t === "sat" && selectedSatellite) {
                api
                  .setFrequency(selectedSatellite.frequency_hz)
                  .then(setSdrStatus)
                  .catch(() => {});
              }
            }}
            className={`flex-1 py-1 rounded uppercase tracking-wider ${
              tuning === t
                ? "bg-accent/20 text-accent"
                : "bg-surface text-text-secondary hover:text-text-primary"
            }`}
          >
            {t === "sat" ? "Satellite" : "Local"}
          </button>
        ))}
      </div>

      {tuning === "sat" ? (
        <div className="text-xs">
          <div className="text-text-secondary uppercase tracking-wider text-[10px]">
            Following
          </div>
          <div className="text-text-primary">
            {selectedSatellite?.name ?? "No satellite selected"}
          </div>
          <div className="text-text-primary tabular-nums">
            {actualMhz != null ? `${actualMhz.toFixed(3)} MHz` : "—"}
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-1 text-xs">
          <label className="text-text-secondary uppercase tracking-wider text-[10px]">
            Frequency (MHz)
          </label>
          <div className="flex gap-1">
            <input
              type="text"
              inputMode="decimal"
              value={localMhz}
              onChange={(e) => setLocalMhz(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") applyLocalFrequency();
              }}
              className="flex-1 px-2 py-1 bg-surface rounded text-text-primary tabular-nums border border-panel-border focus:border-accent outline-none"
              placeholder="100.000"
            />
            <button
              onClick={applyLocalFrequency}
              className="px-2 py-1 rounded bg-accent/20 text-accent hover:bg-accent/30 uppercase tracking-wider"
            >
              Tune
            </button>
          </div>
          <div className="text-text-secondary tabular-nums text-[10px]">
            SDR: {actualMhz != null ? `${actualMhz.toFixed(3)} MHz` : "—"}
          </div>
        </div>
      )}

      <div className="flex gap-1 text-xs">
        {(["off", "wfm", "nfm"] as DemodMode[]).map((m) => (
          <button
            key={m}
            onClick={() => onModeChange(m)}
            className={`flex-1 py-1 rounded uppercase tracking-wider ${
              mode === m
                ? "bg-accent/20 text-accent"
                : "bg-surface text-text-secondary hover:text-text-primary"
            }`}
          >
            {m}
          </button>
        ))}
      </div>

      <button
        onClick={onPlay}
        disabled={mode === "off"}
        className={`py-1.5 rounded text-xs font-bold uppercase tracking-wider ${
          mode === "off"
            ? "bg-surface text-text-secondary cursor-not-allowed"
            : playing
              ? "bg-danger/20 text-danger hover:bg-danger/30"
              : "bg-accent/20 text-accent hover:bg-accent/30"
        }`}
      >
        {playing ? "Stop" : "Play"}
      </button>

      <div className="flex items-center gap-2 text-[10px] text-text-secondary">
        <span>VOL</span>
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={volume}
          onChange={(e) => setVolume(Number(e.target.value))}
          className="flex-1 accent-accent"
        />
        <span className="tabular-nums w-7 text-right">{Math.round(volume * 100)}%</span>
      </div>

      <div className="flex flex-col gap-1 pt-2 border-t border-panel-border">
        <button
          onClick={runScan}
          disabled={scanning}
          className={`py-1.5 rounded text-xs font-bold uppercase tracking-wider ${
            scanning
              ? "bg-surface text-text-secondary cursor-wait"
              : "bg-accent/20 text-accent hover:bg-accent/30"
          }`}
        >
          {scanning ? "Scanning FM…" : "Scan FM Band"}
        </button>
        {scanError && (
          <div className="text-[10px] text-warning">{scanError}</div>
        )}
        {stations && stations.length > 0 && (
          <div className="flex flex-col gap-0.5 max-h-40 overflow-y-auto">
            <div className="text-[10px] text-text-secondary uppercase tracking-wider">
              {stations.length} station{stations.length === 1 ? "" : "s"}
            </div>
            {stations.map((s) => (
              <button
                key={s.frequency_hz}
                onClick={() => tuneToStation(s.frequency_hz)}
                className="flex items-center justify-between px-2 py-1 rounded text-xs bg-surface hover:bg-panel-border text-text-primary"
              >
                <span className="tabular-nums">{(s.frequency_hz / 1e6).toFixed(2)} MHz</span>
                <span className="text-text-secondary tabular-nums text-[10px]">
                  +{s.snr_db.toFixed(0)} dB
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
