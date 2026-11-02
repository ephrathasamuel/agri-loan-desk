// Field boundary helpers. The API recomputes the area from the boundary;
// this copy only shows the officer the area while drawing.

export type LonLat = [number, number];

export interface PolygonGeometry {
  type: "Polygon";
  coordinates: LonLat[][];
}

const EARTH_RADIUS_M = 6371008.8;
const rad = (d: number) => (d * Math.PI) / 180;

/** Geodesic area of a ring in hectares (spherical excess, Chamberlain & Duquette 2007). */
export function ringAreaHa(ring: LonLat[]): number {
  if (ring.length < 3) return 0;
  const closed = ring[0][0] === ring[ring.length - 1][0] && ring[0][1] === ring[ring.length - 1][1]
    ? ring
    : [...ring, ring[0]];
  let total = 0;
  for (let i = 0; i < closed.length - 1; i++) {
    const [lon1, lat1] = closed[i];
    const [lon2, lat2] = closed[i + 1];
    total += rad(lon2 - lon1) * (2 + Math.sin(rad(lat1)) + Math.sin(rad(lat2)));
  }
  return (Math.abs(total) * EARTH_RADIUS_M ** 2) / 2 / 10000;
}

export function toPolygon(corners: LonLat[]): PolygonGeometry {
  return { type: "Polygon", coordinates: [[...corners, corners[0]]] };
}

export function formatHa(ha: number): string {
  if (ha < 10) return `${ha.toFixed(2)} ha`;
  return `${ha.toLocaleString("en-US", { maximumFractionDigits: 1 })} ha`;
}
