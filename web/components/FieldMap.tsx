"use client";

import { useEffect, useRef, useState } from "react";
import type * as Leaflet from "leaflet";
import "leaflet/dist/leaflet.css";
import { formatHa, ringAreaHa, toPolygon, type LonLat, type PolygonGeometry } from "@/lib/geo";

const ETHIOPIA: [number, number] = [8.9, 38.8];

export interface FieldValue {
  boundary: PolygonGeometry | null;
  point: { lat: number; lon: number } | null;
}

interface Props {
  mode: "boundary" | "point";
  onChange: (value: FieldValue) => void;
}

/**
 * Pick a field on the map. In boundary mode each click adds a corner of the
 * field; "Finish" closes the shape. In point mode a click drops a marker.
 */
export default function FieldMap({ mode, onChange }: Props) {
  const holder = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Leaflet.Map | null>(null);
  const LRef = useRef<typeof Leaflet | null>(null);
  const layerRef = useRef<Leaflet.LayerGroup | null>(null);
  const [corners, setCorners] = useState<LonLat[]>([]);
  const [closed, setClosed] = useState(false);
  const [point, setPoint] = useState<{ lat: number; lon: number } | null>(null);
  const [mapVersion, setMapVersion] = useState(0);
  const [goto, setGoto] = useState("");
  const [gotoError, setGotoError] = useState("");
  // The map's click handler is registered once; refs give it the current mode.
  const modeRef = useRef(mode);
  const closedRef = useRef(closed);
  useEffect(() => {
    modeRef.current = mode;
    closedRef.current = closed;
  }, [mode, closed]);

  // Create the map once.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const L = (await import("leaflet")).default;
      if (cancelled || !holder.current || mapRef.current) return;
      LRef.current = L;
      const map = L.map(holder.current, { center: ETHIOPIA, zoom: 6 });
      const streets = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
      });
      const satellite = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        { maxZoom: 19, attribution: "Imagery &copy; Esri, Maxar, Earthstar Geographics" },
      );
      satellite.addTo(map);
      L.control.layers({ Satellite: satellite, Streets: streets }).addTo(map);
      layerRef.current = L.layerGroup().addTo(map);
      map.on("click", (e: Leaflet.LeafletMouseEvent) => {
        const { lat, lng } = e.latlng;
        if (modeRef.current === "point") {
          setPoint({ lat: +lat.toFixed(6), lon: +lng.toFixed(6) });
        } else if (!closedRef.current) {
          setCorners((c) => [...c, [+lng.toFixed(6), +lat.toFixed(6)]]);
        }
      });
      mapRef.current = map;
      // Bump so anything already picked is drawn on the (re)created map.
      setMapVersion((v) => v + 1);
    })();
    return () => {
      cancelled = true;
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  // Redraw what has been picked and report it.
  useEffect(() => {
    const L = LRef.current;
    const layer = layerRef.current;
    if (!L || !layer) return;
    layer.clearLayers();
    const style = { color: "#f59e0b", weight: 3, fillColor: "#fbbf24", fillOpacity: 0.25 };
    if (mode === "boundary") {
      const latlngs = corners.map(([lon, lat]) => [lat, lon] as [number, number]);
      if (closed && corners.length >= 3) {
        L.polygon(latlngs, style).addTo(layer);
      } else if (latlngs.length > 1) {
        L.polyline(latlngs, { ...style, dashArray: "6 6" }).addTo(layer);
      }
      latlngs.forEach((ll, i) =>
        L.circleMarker(ll, {
          radius: i === 0 ? 7 : 5, color: "#fff", weight: 2, fillColor: "#f59e0b", fillOpacity: 1,
        })
          .on("click", (e) => {
            if (i === 0 && corners.length >= 3) {
              L.DomEvent.stopPropagation(e);
              setClosed(true);
            }
          })
          .addTo(layer),
      );
      onChange({ boundary: closed && corners.length >= 3 ? toPolygon(corners) : null, point: null });
    } else {
      if (point) L.marker([point.lat, point.lon]).addTo(layer);
      onChange({ boundary: null, point });
    }
    // onChange is stable enough for this purpose; redraw on picks only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [corners, closed, point, mode, mapVersion]);

  function locate() {
    navigator.geolocation?.getCurrentPosition(
      (pos) => mapRef.current?.setView([pos.coords.latitude, pos.coords.longitude], 16),
      () => undefined,
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  // "8.7512, 38.9801" from a GPS reading or a phone's map app.
  function goToCoordinates() {
    const m = goto.trim().match(/^(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)$/);
    const lat = m ? Number(m[1]) : NaN;
    const lon = m ? Number(m[2]) : NaN;
    if (!m || Math.abs(lat) > 90 || Math.abs(lon) > 180) {
      setGotoError("Enter latitude, longitude, e.g. 8.7512, 38.9801");
      return;
    }
    setGotoError("");
    mapRef.current?.setView([lat, lon], 17);
  }

  function clear() {
    setCorners([]);
    setClosed(false);
    setPoint(null);
  }

  const area = closed ? ringAreaHa(corners) : 0;

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <input
          aria-label="Go to coordinates"
          className="input"
          placeholder="Go to GPS coordinates: latitude, longitude"
          value={goto}
          onChange={(e) => setGoto(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              goToCoordinates();
            }
          }}
        />
        <button type="button" className="btn-secondary shrink-0" onClick={goToCoordinates}>Go</button>
      </div>
      {gotoError ? <p className="text-xs text-red-700">{gotoError}</p> : null}
      <div
        ref={holder}
        data-testid="field-map"
        className="h-[340px] w-full overflow-hidden rounded-lg border border-line sm:h-[420px]"
        aria-label="Map: click to mark the field"
      />
      <div className="flex flex-wrap items-center gap-2 text-sm">
        {mode === "boundary" ? (
          <>
            <button type="button" className="btn-secondary" onClick={() => setClosed(true)}
              disabled={closed || corners.length < 3}>
              Finish shape
            </button>
            <button type="button" className="btn-secondary" onClick={() => setCorners((c) => c.slice(0, -1))}
              disabled={closed || corners.length === 0}>
              Undo corner
            </button>
          </>
        ) : null}
        <button type="button" className="btn-secondary" onClick={clear}>Clear</button>
        <button type="button" className="btn-secondary" onClick={locate}>Go to my location</button>
        <span className="text-muted" data-testid="map-status">
          {mode === "boundary"
            ? closed
              ? `Field drawn: ${corners.length} corners, ${formatHa(area)}`
              : corners.length
                ? `${corners.length} corner${corners.length > 1 ? "s" : ""}. Click the first corner or Finish to close.`
                : "Zoom in and click each corner of the field."
            : point
              ? `Location: ${point.lat.toFixed(4)}, ${point.lon.toFixed(4)}`
              : "Click the field's location."}
        </span>
      </div>
    </div>
  );
}
