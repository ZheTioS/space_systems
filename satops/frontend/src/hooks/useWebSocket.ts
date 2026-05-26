import { useEffect, useRef } from "react";
import { config } from "../config";
import { useStore } from "../store";
import type { Satellite, WsEvent } from "../types";

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const cancelledRef = useRef(false);
  const selectedRef = useRef<Satellite | null>(null);

  const setTracking = useStore((s) => s.setTracking);
  const setSpectrum = useStore((s) => s.setSpectrum);
  const setLinkBudget = useStore((s) => s.setLinkBudget);
  const setActivePass = useStore((s) => s.setActivePass);
  const setWsConnected = useStore((s) => s.setWsConnected);
  const selectedSatellite = useStore((s) => s.selectedSatellite);

  useEffect(() => {
    selectedRef.current = selectedSatellite;
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN && selectedSatellite) {
      ws.send(
        JSON.stringify({
          type: "select_satellite",
          norad_id: selectedSatellite.norad_id,
        }),
      );
    }
  }, [selectedSatellite]);

  useEffect(() => {
    cancelledRef.current = false;

    const connect = (): void => {
      if (cancelledRef.current) return;
      const ws = new WebSocket(config.wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        const sat = selectedRef.current;
        if (sat) {
          ws.send(
            JSON.stringify({ type: "select_satellite", norad_id: sat.norad_id }),
          );
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        if (wsRef.current === ws) wsRef.current = null;
        if (!cancelledRef.current) {
          reconnectTimerRef.current = window.setTimeout(
            connect,
            config.wsReconnectDelayMs,
          );
        }
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
          case "active_pass_cleared":
            setActivePass(null);
            break;
        }
      };
    };

    connect();

    return () => {
      cancelledRef.current = true;
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      const ws = wsRef.current;
      if (ws) {
        ws.onclose = null;
        ws.close();
        wsRef.current = null;
      }
    };
  }, [setTracking, setSpectrum, setLinkBudget, setActivePass, setWsConnected]);
}
