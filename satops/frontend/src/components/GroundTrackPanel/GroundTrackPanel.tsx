import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup, useMap } from "react-leaflet";
import { useStore } from "../../store";
import { api } from "../../services/api";
import type { GroundTrack } from "../../types";
import "leaflet/dist/leaflet.css";

function MapUpdater({ center }: { center: [number, number] | null }) {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.setView(center, map.getZoom(), { animate: true });
    }
  }, [center, map]);
  return null;
}

export function GroundTrackPanel() {
  const selectedSatellite = useStore((s) => s.selectedSatellite);
  const tracking = useStore((s) => s.tracking);
  const [groundTrack, setGroundTrack] = useState<GroundTrack | null>(null);

  // Fetch ground track when satellite changes
  useEffect(() => {
    if (!selectedSatellite) return;
    api.getGroundTrack(selectedSatellite.norad_id).then(setGroundTrack);
    const interval = setInterval(() => {
      api.getGroundTrack(selectedSatellite.norad_id).then(setGroundTrack);
    }, 30_000);
    return () => clearInterval(interval);
  }, [selectedSatellite]);

  // Split track into segments at antimeridian crossings
  const trackSegments: [number, number][][] = [];
  if (groundTrack) {
    let segment: [number, number][] = [];
    for (let i = 0; i < groundTrack.track.length; i++) {
      const pt = groundTrack.track[i];
      if (segment.length > 0) {
        const prev = groundTrack.track[i - 1];
        if (Math.abs(pt.lon - prev.lon) > 180) {
          trackSegments.push(segment);
          segment = [];
        }
      }
      segment.push([pt.lat, pt.lon]);
    }
    if (segment.length > 0) trackSegments.push(segment);
  }

  const satPosition: [number, number] | null =
    tracking?.lat != null && tracking?.lon != null
      ? [tracking.lat, tracking.lon]
      : groundTrack
        ? [groundTrack.current.lat, groundTrack.current.lon]
        : null;

  return (
    <div className="flex flex-col gap-2 p-3 bg-panel rounded border border-panel-border min-h-0 overflow-hidden">
      <h2 className="text-xs font-bold text-text-secondary uppercase tracking-widest shrink-0">
        Ground Track
      </h2>
      <div className="flex-1 min-h-[200px] rounded overflow-hidden">
        <MapContainer
          center={satPosition ?? [52.52, 13.405]}
          zoom={3}
          style={{ height: "100%", width: "100%", background: "#0f1219" }}
          attributionControl={false}
          zoomControl={false}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />

          {/* Ground track path */}
          {trackSegments.map((seg, i) => (
            <Polyline
              key={i}
              positions={seg}
              pathOptions={{ color: "#00ff88", weight: 1.5, opacity: 0.5 }}
            />
          ))}

          {/* Satellite current position */}
          {satPosition && (
            <CircleMarker
              center={satPosition}
              radius={6}
              pathOptions={{ color: "#00ff88", fillColor: "#00ff88", fillOpacity: 1 }}
            >
              <Popup>
                <span style={{ color: "#000" }}>
                  {tracking?.satellite ?? selectedSatellite?.name}
                  <br />
                  {satPosition[0].toFixed(2)}°, {satPosition[1].toFixed(2)}°
                </span>
              </Popup>
            </CircleMarker>
          )}

          {/* Observer position */}
          {groundTrack && (
            <CircleMarker
              center={[groundTrack.observer.lat, groundTrack.observer.lon]}
              radius={5}
              pathOptions={{ color: "#ffaa00", fillColor: "#ffaa00", fillOpacity: 1 }}
            >
              <Popup>
                <span style={{ color: "#000" }}>Ground Station</span>
              </Popup>
            </CircleMarker>
          )}

          <MapUpdater center={satPosition} />
        </MapContainer>
      </div>
    </div>
  );
}
