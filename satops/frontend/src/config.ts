/** Frontend configuration — override via VITE_ environment variables. */

export const config = {
  // Display
  spectrumMinDb: Number(import.meta.env.VITE_SPECTRUM_MIN_DB ?? -120),
  spectrumMaxDb: Number(import.meta.env.VITE_SPECTRUM_MAX_DB ?? -20),
  waterfallRows: Number(import.meta.env.VITE_WATERFALL_ROWS ?? 100),
  maxUpcomingPasses: Number(import.meta.env.VITE_MAX_UPCOMING_PASSES ?? 5),

  // Signal thresholds
  snrGoodDb: Number(import.meta.env.VITE_SNR_GOOD_DB ?? 10),
  snrWarningDb: Number(import.meta.env.VITE_SNR_WARNING_DB ?? 5),

  // WebSocket
  wsReconnectDelayMs: Number(import.meta.env.VITE_WS_RECONNECT_DELAY_MS ?? 3000),
  wsUrl: (import.meta.env.VITE_WS_URL as string) ?? "ws://127.0.0.1:8000/ws",
  audioWsUrl:
    (import.meta.env.VITE_AUDIO_WS_URL as string) ?? "ws://127.0.0.1:8000/api/sdr/audio",
} as const;
