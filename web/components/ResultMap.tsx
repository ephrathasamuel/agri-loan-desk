"use client";

import { useEffect, useRef } from "react";
import "leaflet/dist/leaflet.css";
import type { PolygonGeometry } from "@/lib/geo";

interface Props {
  lat: number;
  lon: number;
  boundary: PolygonGeometry | null;
  cells: number[][]; // NASA POWER grid cell centres [lat, lon]
}

const HALF_LAT = 0.25;
const HALF_LON = 0.3125;

/** The assessed field, plus the NASA POWER grid cells its weather came from. */
export default function ResultMap({ lat, lon, boundary, cells }: Props) {
  const holder = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let map: import("leaflet").Map | null = null;
    let cancelled = false;
    (async () => {
      const L = (await import("leaflet")).default;
      if (cancelled || !holder.current) return;
      map = L.map(holder.current, { scrollWheelZoom: false });
      L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        { maxZoom: 19, attribution: "Imagery &copy; Esri, Maxar, Earthstar Geographics" },
      ).addTo(map);
      const cellLayers = cells.map(([cLat, cLon]) =>
        L.rectangle([[cLat - HALF_LAT, cLon - HALF_LON], [cLat + HALF_LAT, cLon + HALF_LON]], {
          color: "#60a5fa", weight: 2, dashArray: "6 6", fillOpacity: 0.05,
        }).bindTooltip("NASA POWER grid cell used for weather history").addTo(map!),
      );
      const style = { color: "#f59e0b", weight: 3, fillColor: "#fbbf24", fillOpacity: 0.3 };
      if (boundary) {
        const shape = L.polygon(boundary.coordinates[0].map(([x, y]) => [y, x] as [number, number]), style).addTo(map);
        map.fitBounds(shape.getBounds(), { padding: [30, 30], maxZoom: 17 });
      } else {
        L.circleMarker([lat, lon], { ...style, radius: 8 }).addTo(map);
        map.setView([lat, lon], 14);
      }
      // A zoomed-out inset would be nicer; a toggle keeps it simple.
      const fitCells = L.Control.extend({
        onAdd() {
          const btn = L.DomUtil.create("button", "leaflet-bar");
          btn.type = "button";
          btn.textContent = "Show weather grid";
          btn.style.cssText = "background:#fff;padding:4px 8px;font-size:12px;cursor:pointer";
          L.DomEvent.on(btn, "click", (e) => {
            L.DomEvent.stop(e);
            map?.fitBounds(L.featureGroup(cellLayers).getBounds(), { padding: [20, 20] });
          });
          return btn;
        },
      });
      new fitCells({ position: "topright" }).addTo(map);
    })();
    return () => {
      cancelled = true;
      map?.remove();
    };
  }, [lat, lon, boundary, cells]);

  return <div ref={holder} className="h-64 w-full overflow-hidden rounded-lg border border-line sm:h-72" />;
}
