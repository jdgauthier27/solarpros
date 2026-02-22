import { useState, useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import {
  getPropertyMap,
  type GeoJSONCollection,
  type GeoJSONFeature,
} from "../../api/client";

const SOCAL_CENTER: [number, number] = [33.8, -117.8];
const DEFAULT_ZOOM = 8;
const COUNTIES = ["All", "Los Angeles", "Orange", "San Diego", "Riverside", "San Bernardino"];

const TIER_COLORS: Record<string, string> = {
  A: "#16a34a",
  B: "#d97706",
  C: "#dc2626",
};

const TIER_RADIUS: Record<string, number> = {
  A: 7,
  B: 5,
  C: 4,
};

export function PropertyMap() {
  const [county, setCounty] = useState<string>("All");
  const [geojson, setGeojson] = useState<GeoJSONCollection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchMap() {
      try {
        setLoading(true);
        const data = await getPropertyMap(county === "All" ? undefined : county);
        if (!cancelled) {
          setGeojson(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load map data");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchMap();
    return () => { cancelled = true; };
  }, [county]);

  const featureCount = geojson?.features.length ?? 0;
  const tierCounts = geojson?.features.reduce((acc, f) => {
    const t = f.properties.tier ?? "?";
    acc[t] = (acc[t] || 0) + 1;
    return acc;
  }, {} as Record<string, number>) ?? {};

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: "#1a1a2e" }}>Property Map</h1>

      {/* Filter + Legend Bar */}
      <div style={{ display: "flex", alignItems: "center", gap: 16, background: "#fff", padding: "12px 16px", borderRadius: 10, boxShadow: "0 1px 4px rgba(0,0,0,0.08)" }}>
        <label htmlFor="county-filter" style={{ fontSize: 14, fontWeight: 500 }}>County:</label>
        <select id="county-filter" style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #ccc", fontSize: 14 }} value={county} onChange={(e) => setCounty(e.target.value)}>
          {COUNTIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>

        <div style={{ display: "flex", gap: 16, marginLeft: "auto", fontSize: 13 }}>
          {Object.entries(TIER_COLORS).map(([tier, color]) => (
            <span key={tier} style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 12, height: 12, borderRadius: "50%", background: color, display: "inline-block" }} />
              Tier {tier} ({tierCounts[tier] || 0})
            </span>
          ))}
        </div>

        <span style={{ fontSize: 12, color: "#9ca3af" }}>
          {loading ? "Loading..." : `${featureCount} properties`}
        </span>
      </div>

      {error && <div style={{ color: "#d32f2f", padding: 12 }}>Error: {error}</div>}

      {/* Map */}
      <div style={{ borderRadius: 10, overflow: "hidden", boxShadow: "0 1px 4px rgba(0,0,0,0.08)", height: "calc(100vh - 180px)" }}>
        <MapContainer
          center={SOCAL_CENTER}
          zoom={DEFAULT_ZOOM}
          style={{ height: "100%", width: "100%" }}
          scrollWheelZoom={true}
          preferCanvas={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          />

          {!loading && geojson?.features.map((feature: GeoJSONFeature) => {
            const { coordinates } = feature.geometry;
            const props = feature.properties;
            const tierKey = props.tier ?? "";
            const color = TIER_COLORS[tierKey] || "#999";
            const radius = TIER_RADIUS[tierKey] || 4;

            return (
              <CircleMarker
                key={props.id}
                center={[coordinates[1], coordinates[0]]}
                radius={radius}
                pathOptions={{ color: color, fillColor: color, fillOpacity: 0.7, weight: 1 }}
              >
                <Popup>
                  <div style={{ minWidth: 220, fontFamily: "system-ui, sans-serif" }}>
                    <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8 }}>{props.address}</div>
                    <table style={{ fontSize: 12, lineHeight: 1.6, width: "100%" }}>
                      <tbody>
                        <tr><td style={{ color: "#666", paddingRight: 12 }}>County</td><td style={{ fontWeight: 500 }}>{props.county}</td></tr>
                        {props.score != null && <tr><td style={{ color: "#666" }}>Score</td><td><strong>{props.score}</strong> (Tier <strong>{props.tier}</strong>)</td></tr>}
                        {props.owner_name && <tr><td style={{ color: "#666" }}>Owner</td><td>{props.owner_name}</td></tr>}
                        {props.system_size_kw != null && <tr><td style={{ color: "#666" }}>System</td><td>{props.system_size_kw} kW</td></tr>}
                        {props.roof_sqft != null && <tr><td style={{ color: "#666" }}>Roof</td><td>{props.roof_sqft.toLocaleString()} sqft</td></tr>}
                      </tbody>
                    </table>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}

export default PropertyMap;
