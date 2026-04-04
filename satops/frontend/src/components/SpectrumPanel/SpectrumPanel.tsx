import { useEffect, useRef } from "react";
import { config } from "../../config";
import { useStore } from "../../store";

export function SpectrumPanel() {
  const spectrum = useStore((s) => s.spectrum);
  const spectrumCanvasRef = useRef<HTMLCanvasElement>(null);
  const waterfallCanvasRef = useRef<HTMLCanvasElement>(null);

  // Draw spectrum plot
  useEffect(() => {
    if (!spectrum || !spectrumCanvasRef.current) return;
    const canvas = spectrumCanvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const { width, height } = canvas;
    const data = spectrum.magnitudes_db;
    const len = data.length;

    ctx.fillStyle = "#0f1219";
    ctx.fillRect(0, 0, width, height);

    // Grid lines
    ctx.strokeStyle = "#1a1f2e";
    ctx.lineWidth = 1;
    for (let i = 0; i < 5; i++) {
      const y = (height / 5) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Spectrum line
    ctx.strokeStyle = "#00ff88";
    ctx.lineWidth = 1.5;
    ctx.beginPath();

    const minDb = config.spectrumMinDb;
    const maxDb = config.spectrumMaxDb;

    for (let i = 0; i < len; i++) {
      const x = (i / len) * width;
      const normalized = (data[i] - minDb) / (maxDb - minDb);
      const y = height - Math.max(0, Math.min(1, normalized)) * height;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }, [spectrum]);

  // Draw waterfall
  useEffect(() => {
    if (!spectrum || !waterfallCanvasRef.current) return;
    const canvas = waterfallCanvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const { width, height } = canvas;
    const data = spectrum.magnitudes_db;
    const rowHeight = Math.max(1, Math.ceil(height / config.waterfallRows));

    // Shift existing content down by copying canvas onto itself
    ctx.drawImage(canvas, 0, 0, width, height, 0, rowHeight, width, height);

    // Draw new row at top
    const minDb = config.spectrumMinDb;
    const maxDb = config.spectrumMaxDb;
    const pixelWidth = Math.ceil(width / data.length) + 1;

    for (let i = 0; i < data.length; i++) {
      const normalized = (data[i] - minDb) / (maxDb - minDb);
      const clamped = Math.max(0, Math.min(1, normalized));
      // Blue (cold/weak) -> Red (hot/strong)
      const r = Math.floor(clamped * 255);
      const g = Math.floor(clamped * 128);
      const b = Math.floor((1 - clamped) * 255);
      ctx.fillStyle = `rgb(${r},${g},${b})`;
      const x = (i / data.length) * width;
      ctx.fillRect(x, 0, pixelWidth, rowHeight);
    }
  }, [spectrum]);

  return (
    <div className="flex flex-col gap-2 p-3 bg-panel rounded border border-panel-border h-full">
      <h2 className="text-xs font-bold text-text-secondary uppercase tracking-widest">
        Spectrum
      </h2>
      <canvas
        ref={spectrumCanvasRef}
        width={800}
        height={200}
        className="w-full rounded bg-surface"
        style={{ imageRendering: "pixelated" }}
      />

      <h2 className="text-xs font-bold text-text-secondary uppercase tracking-widest">
        Waterfall
      </h2>
      <canvas
        ref={waterfallCanvasRef}
        width={800}
        height={200}
        className="w-full rounded bg-surface flex-1"
        style={{ imageRendering: "pixelated" }}
      />
    </div>
  );
}
