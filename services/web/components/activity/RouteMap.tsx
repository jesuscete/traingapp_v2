"use client";

import "leaflet/dist/leaflet.css";

import { useEffect, useRef } from "react";

type LatLng = [number, number];

function validPoint(lat: number | null | undefined, lon: number | null | undefined): boolean {
  return (
    typeof lat === "number" &&
    typeof lon === "number" &&
    Math.abs(lat) <= 90 &&
    Math.abs(lon) <= 180 &&
    !(lat === 0 && lon === 0)
  );
}

export function routePoints(
  lat: (number | null)[] | undefined,
  lon: (number | null)[] | undefined,
): LatLng[] {
  if (!lat || !lon) return [];
  const out: LatLng[] = [];
  for (let i = 0; i < Math.min(lat.length, lon.length); i++) {
    const a = lat[i];
    const b = lon[i];
    if (validPoint(a, b)) out.push([a as number, b as number]);
  }
  return out;
}

/** Recorrido sobre OpenStreetMap. Leaflet se carga en el cliente (usa `window`). */
export function RouteMap({ points }: { points: LatLng[] }) {
  const container = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const node = container.current;
    if (!node || points.length < 2) return;
    let disposed = false;
    let cleanup: (() => void) | null = null;

    void import("leaflet").then((L) => {
      if (disposed) return;
      const map = L.map(node, { scrollWheelZoom: false, attributionControl: true });
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap",
      }).addTo(map);
      const line = L.polyline(points, { color: "#3b82f6", weight: 4 }).addTo(map);
      const dot = (p: LatLng, color: string) =>
        L.circleMarker(p, { radius: 6, color: "#fff", weight: 2, fillColor: color, fillOpacity: 1 });
      dot(points[0], "#2fd9a8").addTo(map).bindTooltip("Salida");
      dot(points[points.length - 1], "#ef4444").addTo(map).bindTooltip("Llegada");
      map.fitBounds(line.getBounds(), { padding: [16, 16] });
      cleanup = () => map.remove();
    });

    return () => {
      disposed = true;
      cleanup?.();
    };
  }, [points]);

  if (points.length < 2) return null;
  return <div ref={container} className="route-map" role="img" aria-label="Mapa del recorrido" />;
}
