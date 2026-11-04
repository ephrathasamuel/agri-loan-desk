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

interface Place {
  id: number;
  name: string;
  admin1?: string;
  country?: string;
  latitude: number;
  longitude: number;
  feature_code?: string;
}

// "8.7512, 38.9801" from a GPS reading or a phone's map app.
function parseCoordinates(text: string): [number, number] | null {
  const m = text.trim().match(/^(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)$/);
  if (!m) return null;
  const lat = Number(m[1]);
  const lon = Number(m[2]);
  return Math.abs(lat) <= 90 && Math.abs(lon) <= 180 ? [lat, lon] : null;
}

// A round, finger-sized handle for a corner; the first corner is larger because clicking it closes the shape.
function cornerIcon(L: typeof Leaflet, first: boolean) {
  const size = first ? 22 : 18;
  return L.divIcon({
    className: "",
    // Styled inline: Leaflet adds this markup outside React, after the stylesheet is processed.
    html: `<span style="display:block;width:100%;height:100%;box-sizing:border-box;border:3px solid #fff;border-radius:9999px;background:${first ? "#14532d" : "#f59e0b"};box-shadow:0 1px 4px rgb(0 0 0 / .45);cursor:grab"></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

/**
 * Pick a field on the map. In boundary mode each click adds a corner of the
 * field and corners can be dragged; "Finish" closes the shape. In point mode a
 * click drops a marker that can also be dragged.
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
  const [query, setQuery] = useState("");
  const [places, setPlaces] = useState<Place[]>([]);
  const [searchNote, setSearchNote] = useState("");
  const [searching, setSearching] = useState(false);
  const [fullScreen, setFullScreen] = useState(false);
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
    const el = holder.current;
    let onWheel: ((e: WheelEvent) => void) | null = null;
    (async () => {
      const L = (await import("leaflet")).default;
      if (cancelled || !el || mapRef.current) return;
      LRef.current = L;
      // zoomSnap 0 lets a trackpad pinch zoom smoothly instead of in jumps.
      const map = L.map(el, { center: ETHIOPIA, zoom: 6, zoomSnap: 0, zoomDelta: 1, scrollWheelZoom: false });
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

      // Trackpads: a two-finger swipe moves the map in any direction and a pinch zooms.
      // A mouse wheel (whole steps, no sideways part) zooms, as before.
      onWheel = (e: WheelEvent) => {
        e.preventDefault();
        const mouseWheel = e.deltaX === 0 && (e.deltaMode !== 0 || (Number.isInteger(e.deltaY) && Math.abs(e.deltaY) >= 50));
        if (e.ctrlKey || mouseWheel) {
          const step = e.ctrlKey ? -e.deltaY / 100 : e.deltaY < 0 ? 1 : -1;
          const zoom = Math.min(map.getMaxZoom(), Math.max(map.getMinZoom(), map.getZoom() + step));
          map.setZoomAround(map.mouseEventToContainerPoint(e), zoom, { animate: !e.ctrlKey });
        } else {
          map.panBy([e.deltaX, e.deltaY], { animate: false });
        }
      };
      el.addEventListener("wheel", onWheel, { passive: false });

      mapRef.current = map;
      // Bump so anything already picked is drawn on the (re)created map.
      setMapVersion((v) => v + 1);
    })();
    return () => {
      cancelled = true;
      if (el && onWheel) el.removeEventListener("wheel", onWheel);
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
        L.polygon(latlngs, { ...style, interactive: false }).addTo(layer);
      } else if (latlngs.length > 1) {
        L.polyline(latlngs, { ...style, dashArray: "6 6", interactive: false }).addTo(layer);
      }
      latlngs.forEach((ll, i) =>
        L.marker(ll, { icon: cornerIcon(L, i === 0), draggable: true, title: `Corner ${i + 1}: drag to move` })
          .on("click", (e) => {
            L.DomEvent.stopPropagation(e);
            if (i === 0 && corners.length >= 3) setClosed(true);
          })
          .on("dragend", (e) => {
            const { lat, lng } = (e.target as Leaflet.Marker).getLatLng();
            setCorners((c) => c.map((p, j) => (j === i ? [+lng.toFixed(6), +lat.toFixed(6)] : p)));
          })
          .addTo(layer),
      );
      onChange({ boundary: closed && corners.length >= 3 ? toPolygon(corners) : null, point: null });
    } else {
      if (point) {
        L.marker([point.lat, point.lon], { draggable: true, title: "Drag to move" })
          .on("dragend", (e) => {
            const { lat, lng } = (e.target as Leaflet.Marker).getLatLng();
            setPoint({ lat: +lat.toFixed(6), lon: +lng.toFixed(6) });
          })
          .addTo(layer);
      }
      onChange({ boundary: null, point });
    }
    // onChange is stable enough for this purpose; redraw on picks only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [corners, closed, point, mode, mapVersion]);

  // The map must re-measure itself once it has grown or shrunk; Esc leaves full screen.
  useEffect(() => {
    const frame = requestAnimationFrame(() => mapRef.current?.invalidateSize());
    if (!fullScreen) return () => cancelAnimationFrame(frame);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setFullScreen(false);
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [fullScreen]);

  function locate() {
    navigator.geolocation?.getCurrentPosition(
      (pos) => mapRef.current?.setView([pos.coords.latitude, pos.coords.longitude], 17),
      () => setSearchNote("Your location is not available. Allow location access or search for the place."),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  function goTo(place: Place) {
    // Towns and villages open close enough to see fields; regions further out.
    const zoom = place.feature_code?.startsWith("PPL") ? 15 : 11;
    mapRef.current?.setView([place.latitude, place.longitude], zoom);
    setPlaces([]);
    setSearchNote(`Showing ${place.name}. Zoom in to find the field.`);
  }

  // A town, village or kebele name, or GPS coordinates.
  async function search() {
    setSearchNote("");
    setPlaces([]);
    const coords = parseCoordinates(query);
    if (coords) {
      mapRef.current?.setView(coords, 17);
      return;
    }
    if (query.trim().length < 2) {
      setSearchNote("Type a town or village name, or GPS coordinates such as 8.7512, 38.9801.");
      return;
    }
    setSearching(true);
    try {
      const url = `https://geocoding-api.open-meteo.com/v1/search?count=6&language=en&format=json&name=${encodeURIComponent(query.trim())}`;
      const results: Place[] = (await (await fetch(url)).json()).results ?? [];
      // The gazetteer can list one town twice (e.g. as a town and a district seat).
      const seen = new Set<string>();
      const found = results.filter((p) => {
        const key = `${p.name}|${p.admin1}|${p.country}`;
        return !seen.has(key) && seen.add(key);
      });
      // Ethiopian places first: that is where the desk lends.
      found.sort((a, b) => Number(b.country === "Ethiopia") - Number(a.country === "Ethiopia"));
      if (!found.length) setSearchNote(`No place called "${query.trim()}" was found. Try a nearby town, or use coordinates.`);
      else if (found.length === 1) goTo(found[0]);
      else setPlaces(found);
    } catch {
      setSearchNote("Place search is not available right now. Use coordinates or move the map.");
    } finally {
      setSearching(false);
    }
  }

  function clear() {
    setCorners([]);
    setClosed(false);
    setPoint(null);
  }

  const area = closed ? ringAreaHa(corners) : 0;

  return (
    <div className={fullScreen ? "fixed inset-0 z-[2000] flex flex-col gap-2 bg-white p-3" : "space-y-2"}>
      <div className="relative">
        <div className="flex gap-2">
          <input
            aria-label="Find a place"
            className="input"
            placeholder="Town, village or GPS coordinates"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                search();
              }
            }}
          />
          <button type="button" className="btn-secondary shrink-0" onClick={search} disabled={searching}>
            Go
          </button>
        </div>
        {places.length ? (
          <ul className="absolute inset-x-0 top-full z-[1100] mt-1 overflow-hidden rounded-lg border border-line bg-white shadow-lg">
            {places.map((p) => (
              <li key={p.id}>
                <button type="button" className="w-full px-3 py-2 text-left text-sm hover:bg-slate-50" onClick={() => goTo(p)}>
                  <span className="font-medium">{p.name}</span>
                  <span className="text-muted">{[p.admin1, p.country].filter(Boolean).map((s) => `, ${s}`).join("")}</span>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
      {searchNote ? <p className="text-xs text-muted">{searchNote}</p> : null}
      {/* The size lives on a wrapper: Leaflet adds its own classes to the map element, which a changing className would wipe. */}
      <div className={fullScreen ? "min-h-0 flex-1" : "h-[380px] sm:h-[460px]"}>
        <div
          ref={holder}
          data-testid="field-map"
          className="field-map h-full w-full overflow-hidden rounded-lg border border-line"
          aria-label="Map: click to mark the field"
        />
      </div>
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
        <button type="button" className="btn-secondary" onClick={locate}>My location</button>
        <button type="button" className={fullScreen ? "btn-primary" : "btn-secondary"} onClick={() => setFullScreen((f) => !f)}>
          {fullScreen ? "Done" : "Full screen"}
        </button>
        <span className="text-muted" data-testid="map-status">
          {mode === "boundary"
            ? closed
              ? `Field drawn: ${corners.length} corners, ${formatHa(area)}. Drag a corner to adjust it.`
              : corners.length
                ? `${corners.length} corner${corners.length > 1 ? "s" : ""}. Drag any corner to adjust. Click the first corner or Finish to close.`
                : "Find the field, zoom in, then click each corner."
            : point
              ? `Location: ${point.lat.toFixed(4)}, ${point.lon.toFixed(4)}. Drag the pin to adjust.`
              : "Click the field's location."}
        </span>
      </div>
      <p className="text-xs text-muted">
        Move the map by dragging, or with a two-finger swipe on a trackpad. Zoom with the + and − buttons, the mouse wheel, or a pinch.
      </p>
    </div>
  );
}
