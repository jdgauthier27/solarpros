import React, { useState, useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import {
  getPropertyMap,
  type GeoJSONCollection,
  type GeoJSONFeature,
} from "../../api/client";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SOCAL_CENTER: [number, number] = [33.8, -117.8];
const DEFAULT_ZOOM = 8;

const COUNTIES = ["All", "Los Angeles", "Orange", "San Diego", "Riverside", "San Bernardino"];

const TIER_COLORS: Record<string, string> = {
  A: "#4caf50",
  B: "#ff9800",
  C: "#f44336",
};

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const containerStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 16,
};

const headerStyle: React.CSSProperties = {
  fontSize: 24,
  fontWeight: 700,
  color: "#1a1a2e",
};

const filterBarStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 12,
  background: "#fff",
  padding: "12px 16px",
  borderRadius: 10,
  boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
};

const selectStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: 6,
  border: "1px solid #ccc",
  fontSize: 14,
  outline: "none",
};

const mapWrapperStyle: React.CSSProperties = {
  borderRadius: 10,
  overflow: "hidden",
  boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
  height: "calc(100vh - 180px)",
};

const legendStyle: React.CSSProperties = {
  display: "flex",
  gap: 16,
  marginLeft: "auto",
  fontSize: 13,
};

const legendDotStyle = (color: string): React.CSSProperties => ({
  width: 12,
  height: 12,
  borderRadius: "50%",
  background: color,
  display: "inline-block",
  marginRight: 4,
  verticalAlign: "middle",
});

const popupLabelStyle: React.CSSProperties = {
  fontWeight: 600,
  fontSize: 13,
  color: "#333",
};

const popupValueStyle: React.CSSProperties = {
  fontSize: 13,
  color: "#555",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

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
    return () => {
      cancelled = true;
    };
  }, [county]);

  return (
    <div style={containerStyle}>
      <h1 style={headerStyle}>Property Map</h1>

      {/* Filter Bar */}
      <div style={filterBarStyle}>
        <label htmlFor="county-filter" style={{ fontSize: 14, fontWeight: 500 }}>
          County:
        </label>
        <select
          id="county-filter"
          style={selectStyle}
          value={county}
          onChange={(e) => setCounty(e.target.value)}
        >
          {COUNTIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        <div style={legendStyle}>
          {Object.entries(TIER_COLORS).map(([tier, color]) => (
            <span key={tier}>
              <span style={legendDotStyle(color)} />
              Tier {tier}
            </span>
          ))}
        </div>
      </div>

      {error && (
        <div style={{ color: "#d32f2f", padding: 12 }}>Error: {error}</div>
      )}

      {/* Map */}
      <div style={mapWrapperStyle}>
        <MapContainer
          center={SOCAL_CENTER}
          zoom={DEFAULT_ZOOM}
          style={{ height: "100%", width: "100%" }}
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {!loading &&
            geojson?.features.map((feature: GeoJSONFeature) => {
              const { coordinates } = feature.geometry;
              const props = feature.properties;
              const color = TIER_COLORS[props.tier ?? ""] || "#999";

              return (
                <CircleMarker
                  key={props.id}
                  center={[coordinates[1], coordinates[0]]}
                  radius={7}
                  pathOptions={{
                    color,
                    fillColor: color,
                    fillOpacity: 0.7,
                    weight: 1,
                  }}
                >
                  <Popup>
                    <div style={{ minWidth: 180 }}>
                      <div style={popupLabelStyle}>{props.address}</div>
                      <div style={{ marginTop: 6 }}>
                        <span style={popupLabelStyle}>Score: </span>
                        <span style={popupValueStyle}>{props.score}</span>
                      </div>
                      <div>
                        <span style={popupLabelStyle}>Tier: </span>
                        <span style={popupValueStyle}>{props.tier}</span>
                      </div>
                      <div>
                        <span style={popupLabelStyle}>Owner: </span>
                        <span style={popupValueStyle}>
                          {props.owner_name || "N/A"}
                        </span>
                      </div>
                      {props.system_size_kw != null && (
                        <div>
                          <span style={popupLabelStyle}>System: </span>
                          <span style={popupValueStyle}>
                            {props.system_size_kw} kW
                          </span>
                        </div>
                      )}
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
