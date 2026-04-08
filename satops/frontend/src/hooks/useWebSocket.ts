import { useEffect, useRef } from "react";
import { config } from "../config";
import { useStore } from "../store";
import type { WsEvent } from "../types";

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const setTracking = useStore((s) => s.setTracking);
  const setSpectrum = useStore((s) => s.setSpectrum);
  const setLinkBudget = useStore((s) => s.setLinkBudget);
  const setActivePass = useStore((s) => s.setActivePass);
  const setWsConnected = useStore((s) => s.setWsConnected);
  const selectedSatellite = useStore((s) => s.selectedSatellite);

  useEffect(() => {
    const ws = new WebSocket(config.wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => {
      setWsConnected(false);
      setTimeout(() => {
        if (wsRef.current === ws) {
          wsRef.current = null;
        }
      }, config.wsReconnectDelayMs);
    };

    ws.onmessage = (event) => {
      const data: WsEvent = JSON.parse(event.data);
      switch (data.type) {
        case "tracking_update":
          setTracking(data);
          break;
        case "spectrum_update":
          setSpectrum(data);
          break;
        case "link_budget":
          setLinkBudget(data);
          break;
        case "active_pass":
          setActivePass(data);
          break;
      }
    };

    return () => {
      ws.close();
    };
  }, [setTracking, setSpectrum, setLinkBudget, setActivePass, setWsConnected]);

  // Send satellite selection to backend when it changes
  useEffect(() => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN && selectedSatellite) {
      ws.send(JSON.stringify({
        type: "select_satellite",
        norad_id: selectedSatellite.norad_id,
      }));
    }
  }, [selectedSatellite]);
}
