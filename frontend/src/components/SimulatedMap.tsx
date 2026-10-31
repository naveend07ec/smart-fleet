import React, { useEffect, useState, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Rectangle, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Navigation, Compass, Crosshair, Radio } from 'lucide-react';
import { Vehicle } from '../types';

// Spherical bearing calculation between two consecutive coordinates
function calculateBearing(start: [number, number], end: [number, number]): number {
  const startLat = (start[0] * Math.PI) / 180;
  const startLng = (start[1] * Math.PI) / 180;
  const endLat = (end[0] * Math.PI) / 180;
  const endLng = (end[1] * Math.PI) / 180;

  const dLng = endLng - startLng;
  const y = Math.sin(dLng) * Math.cos(endLat);
  const x =
    Math.cos(startLat) * Math.sin(endLat) -
    Math.sin(startLat) * Math.cos(endLat) * Math.cos(dLng);

  const brng = (Math.atan2(y, x) * 180) / Math.PI;
  return (brng + 360) % 360;
}

// Modern Precision Vehicle Location Dot with pulse aura (No arrows, perfectly centered)
const createVehicleDotIcon = (status: string, isSelected: boolean = false) => {
  let mainColor = '#059669'; // moving - emerald
  let glowColor = 'rgba(5, 150, 105, 0.4)';
  if (status === 'idle') {
    mainColor = '#D97706'; // idle - amber
    glowColor = 'rgba(217, 119, 6, 0.4)';
  }
  if (status === 'offline') {
    mainColor = '#DC2626'; // offline - red
    glowColor = 'rgba(220, 38, 38, 0.4)';
  }

  const size = isSelected ? 30 : 22;
  const half = size / 2;

  const svgHtml = `
    <div style="position: relative; width: ${size}px; height: ${size}px; display: flex; align-items: center; justify-content: center; pointer-events: auto;">
      <!-- Subtle Pulsing Radar Aura when moving -->
      ${status === 'moving' ? `
        <div class="sim-pulse-ring" style="
          position: absolute;
          width: ${size + 14}px;
          height: ${size + 14}px;
          border-radius: 50%;
          background: ${glowColor};
          pointer-events: none;
        "></div>
      ` : ''}

      <!-- Clean Precision Location Dot -->
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" width="${size}" height="${size}" style="filter: drop-shadow(0 2px 5px rgba(0,0,0,0.35)); display: block;">
        <!-- Outer White Halo Ring -->
        <circle cx="${half}" cy="${half}" r="${half - 1}" fill="#FFFFFF" stroke="rgba(0,0,0,0.18)" stroke-width="1.2"/>
        <!-- Mid Status Circle -->
        <circle cx="${half}" cy="${half}" r="${half - 3}" fill="${mainColor}" />
        <!-- Inner Core Highlight Dot -->
        <circle cx="${half}" cy="${half}" r="${half > 12 ? 4 : 3}" fill="#FFFFFF" />
      </svg>
    </div>
  `;

  return L.divIcon({
    html: svgHtml,
    className: 'sim-vehicle-marker',
    iconSize: [size, size],
    iconAnchor: [half, half],
    popupAnchor: [0, -half],
  });
};

const createGoogleMapsVehicleIcon = (status: string, _heading: number = 0, isSelected: boolean = false) =>
  createVehicleDotIcon(status, isSelected);

const createStartMarkerIcon = () => {
  return L.divIcon({
    html: `
      <div style="background: #0A0A0A; color: white; border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; border: 2px solid #E2E8F0; box-shadow: 0 2px 6px rgba(0,0,0,0.25);">
        S
      </div>
    `,
    className: 'sim-start-marker',
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
};

// Smooth Camera Follower component
interface MapUpdaterProps {
  center: [number, number];
  autoFollow: boolean;
  zoom: number;
}

const MapUpdater: React.FC<MapUpdaterProps> = ({ center, autoFollow, zoom }) => {
  const map = useMap();
  const prevCenterRef = useRef<[number, number]>(center);

  useEffect(() => {
    if (autoFollow && center && center[0] && center[1]) {
      const prev = prevCenterRef.current;
      const dist = Math.hypot(center[0] - prev[0], center[1] - prev[1]);
      // If moved or initial pan, smoothly panTo
      if (dist > 0.00005) {
        map.panTo(center, { animate: true, duration: 1.2 });
        prevCenterRef.current = center;
      }
    }
  }, [center[0], center[1], autoFollow, map]);

  return null;
};

interface SimulatedMapProps {
  vehicles: Vehicle[];
  onSelectVehicle?: (id: number) => void;
  center?: [number, number];
  zoom?: number;
  pathTrail?: [number, number][];
  autoFollow?: boolean;
}

export const SimulatedMap: React.FC<SimulatedMapProps> = ({
  vehicles,
  onSelectVehicle,
  center = [13.05, 80.20],
  zoom = 13,
  pathTrail = [],
  autoFollow: initialAutoFollow = false
}) => {
  const [following, setFollowing] = useState<boolean>(initialAutoFollow);

  // Demo simulation boundary
  const demoBounds: [[number, number], [number, number]] = [
    [12.9000, 80.1000],
    [13.1500, 80.3000]
  ];

  // Primary vehicle if single view
  const primaryVehicle = vehicles.length === 1 ? vehicles[0] : null;
  const primaryTelemetry = primaryVehicle?.latest_telemetry;

  // Compute live heading from recent path points
  const liveHeading = React.useMemo(() => {
    if (pathTrail.length >= 2) {
      const pPrev = pathTrail[pathTrail.length - 2];
      const pLatest = pathTrail[pathTrail.length - 1];
      return calculateBearing(pPrev, pLatest);
    }
    return 45; // Default orientation
  }, [pathTrail]);

  return (
    <div className="map-container" style={{ position: 'relative' }}>
      {/* HUD Header Bar */}
      <div style={{
        position: 'absolute',
        top: 12,
        left: 12,
        zIndex: 500,
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        flexWrap: 'wrap'
      }}>
        <div style={{
          background: 'rgba(15, 23, 42, 0.88)',
          backdropFilter: 'blur(6px)',
          border: '1px solid rgba(51, 65, 85, 0.8)',
          color: '#f8fafc',
          padding: '6px 12px',
          borderRadius: '8px',
          fontSize: '0.78rem',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.4)'
        }}>
          <span style={{
            display: 'inline-block',
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: primaryVehicle?.status === 'moving' ? '#10b981' : '#f59e0b',
            boxShadow: primaryVehicle?.status === 'moving' ? '0 0 8px #10b981' : 'none'
          }} />
          <strong>LIVE GPS NAVIGATION</strong>
          {primaryTelemetry && (
            <span style={{ color: '#93c5fd', fontFamily: 'monospace' }}>
              {primaryTelemetry.latitude.toFixed(4)}, {primaryTelemetry.longitude.toFixed(4)}
            </span>
          )}
          {primaryTelemetry && (
            <span style={{ color: '#34d399', fontWeight: 700 }}>
              {primaryTelemetry.speed} km/h
            </span>
          )}
        </div>

        {/* Follow Vehicle Toggle */}
        <button
          onClick={() => setFollowing(!following)}
          style={{
            background: following ? 'rgba(16, 185, 129, 0.25)' : 'rgba(15, 23, 42, 0.88)',
            border: `1px solid ${following ? '#10b981' : '#334155'}`,
            color: following ? '#34d399' : '#94a3b8',
            padding: '6px 10px',
            borderRadius: '8px',
            fontSize: '0.76rem',
            fontWeight: 600,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backdropFilter: 'blur(6px)',
            transition: 'all 0.2s ease'
          }}
          title="Keep map automatically centered on vehicle as it moves"
        >
          <Crosshair size={14} />
          {following ? 'Following Vehicle: ON' : 'Follow Vehicle: OFF'}
        </button>
      </div>

      {/* Synthetic Banner */}
      <div style={{
        position: 'absolute',
        top: 12,
        right: 12,
        zIndex: 500,
        background: 'rgba(15, 23, 42, 0.88)',
        backdropFilter: 'blur(6px)',
        border: '1px solid #334155',
        color: '#93c5fd',
        padding: '6px 12px',
        borderRadius: '8px',
        fontSize: '0.75rem',
        fontWeight: 600,
        letterSpacing: '0.04em'
      }}>
        📍 CHENNAI SYNTHETIC V2X ROUTE
      </div>

      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom={true}
        style={{ height: '100%', width: '100%', background: '#0f172a' }}
      >
        <MapUpdater center={center} autoFollow={following} zoom={zoom} />

        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Demo Geographic Bounding Box */}
        <Rectangle
          bounds={demoBounds}
          pathOptions={{ color: '#6366f1', weight: 1.5, fillOpacity: 0.04, dashArray: '6, 6' }}
        />

        {/* Traveled Breadcrumb Route Polyline */}
        {pathTrail.length >= 2 && (
          <>
            {/* Soft Cyan/Blue Outer Glow */}
            <Polyline
              positions={pathTrail}
              pathOptions={{ color: '#0ea5e9', weight: 8, opacity: 0.35, lineCap: 'round', lineJoin: 'round' }}
            />
            {/* Core Solid Breadcrumb Line */}
            <Polyline
              positions={pathTrail}
              pathOptions={{ color: '#38bdf8', weight: 4, opacity: 0.95, lineCap: 'round', lineJoin: 'round' }}
            />
            {/* Initial Starting Point Waypoint Pin */}
            <Marker position={pathTrail[0]} icon={createStartMarkerIcon()}>
              <Popup>
                <div style={{ fontSize: '0.82rem', padding: '2px' }}>
                  <strong>Trip Departure Origin</strong>
                  <div style={{ color: '#64748b', fontSize: '0.74rem' }}>
                    {pathTrail[0][0].toFixed(5)}, {pathTrail[0][1].toFixed(5)}
                  </div>
                </div>
              </Popup>
            </Marker>
          </>
        )}

        {/* Vehicle Markers */}
        {vehicles.map((v) => {
          const tel = v.latest_telemetry;
          if (!tel) return null;

          const isSingle = vehicles.length === 1;
          const heading = isSingle ? liveHeading : 45;

          return (
            <Marker
              key={v.id}
              position={[tel.latitude, tel.longitude]}
              icon={createGoogleMapsVehicleIcon(v.status, heading, isSingle)}
            >
              <Popup>
                <div style={{ fontSize: '0.85rem', color: '#0f172a', padding: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                    <strong style={{ fontSize: '0.96rem' }}>{v.name}</strong>
                    <span style={{
                      fontSize: '0.72rem',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontWeight: 700,
                      background: v.status === 'moving' ? '#d1fae5' : '#fef3c7',
                      color: v.status === 'moving' ? '#065f46' : '#92400e'
                    }}>
                      {v.status.toUpperCase()}
                    </span>
                  </div>
                  <div style={{ color: '#475569', fontSize: '0.78rem', marginBottom: '8px' }}>
                    ID: <code>{v.vehicle_identifier}</code>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '0.8rem' }}>
                    <div><strong>Current Speed:</strong> {tel.speed} km/h</div>
                    <div><strong>Battery:</strong> {tel.battery_level}%</div>
                    <div><strong>Heading:</strong> {Math.round(heading)}°</div>
                    <div><strong>GPS Fix:</strong> 3D Lock</div>
                  </div>
                  <div style={{ marginTop: '6px', fontSize: '0.75rem', color: '#64748B', fontFamily: 'var(--font-family-mono)' }}>
                    {tel.latitude.toFixed(6)}, {tel.longitude.toFixed(6)}
                  </div>
                  {onSelectVehicle && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectVehicle(v.id);
                      }}
                      style={{
                        width: '100%',
                        marginTop: '10px',
                        padding: '7px 12px',
                        background: '#0A0A0A',
                        color: '#FFFFFF',
                        border: 'none',
                        borderRadius: '9999px',
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '6px',
                        boxShadow: '0 2px 6px rgba(0, 0, 0, 0.15)'
                      }}
                    >
                      View Live Telemetry & Route →
                    </button>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
};
