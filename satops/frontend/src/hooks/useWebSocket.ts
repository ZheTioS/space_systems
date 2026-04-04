import { useEffect, useRef } from "react";
import { config } from "../config";
import { useStore } from "../store";
import type { WsEvent } from "../types";

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const setTracking = useStore((s) => s.setTracking);
  const setSpectrum = useStore((s) => s.setSpectrum);
  const setLinkBudget = useStore((s) => s.setLinkBudget);
  const setWsConnected = useStore((s) => s.setWsConnected);

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
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
      }
    };

    return () => {
      ws.close();
    };
  }, [setTracking, setSpectrum, setLinkBudget, setWsConnected]);
}
