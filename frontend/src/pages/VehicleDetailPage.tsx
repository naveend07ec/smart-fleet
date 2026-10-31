import React, { useEffect, useState } from 'react';
import { ArrowLeft, MapPin, Gauge, Battery, Clock, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import { VehicleDetail, TelemetryPagination } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { SimulatedMap } from '../components/SimulatedMap';

interface VehicleDetailPageProps {
  vehicleId: number;
  onBack: () => void;
}

export const VehicleDetailPage: React.FC<VehicleDetailPageProps> = ({ vehicleId, onBack }) => {
  const [vehicle, setVehicle] = useState<VehicleDetail | null>(null);
  const [telemetryPage, setTelemetryPage] = useState<TelemetryPagination | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadVehicleData = async () => {
    try {
      const [vData, tData] = await Promise.all([
        api.getVehicle(vehicleId),
        api.getVehicleTelemetry(vehicleId, page, 30),
      ]);
      setVehicle(vData);
      setTelemetryPage(tData);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load vehicle details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVehicleData();
    const interval = setInterval(loadVehicleData, 2000);
    return () => clearInterval(interval);
  }, [vehicleId, page]);

  const pathTrail: [number, number][] = React.useMemo(() => {
    if (!telemetryPage?.items || telemetryPage.items.length === 0) return [];
    return [...telemetryPage.items]
      .reverse()
      .map((t) => [t.latitude, t.longitude] as [number, number]);
  }, [telemetryPage]);

  if (loading && !vehicle) {
    return (
      <div className="state-container">
        <div className="spinner" />
        <div className="state-title">Loading Vehicle Telemetry...</div>
      </div>
    );
  }

  if (error || !vehicle) {
    return (
      <div className="state-container">
        <AlertCircle size={40} color="#f87171" />
        <div className="state-title">Vehicle Not Found</div>
        <p>{error || 'Requested vehicle telemetry could not be loaded.'}</p>
        <button className="btn btn-secondary" onClick={onBack}>
          <ArrowLeft size={16} /> Return to Fleet
        </button>
      </div>
    );
  }

  const latest = vehicle.latest_telemetry;

  return (
    <div className="page-container" data-testid="vehicle-detail-page">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <button className="btn btn-secondary" onClick={onBack} id="btn-back-to-fleet">
          <ArrowLeft size={16} /> Back to Fleet
        </button>
        <button className="btn btn-secondary" onClick={loadVehicleData}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Vehicle Header Card */}
      <div className="panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>{vehicle.name}</h2>
              <StatusBadge status={vehicle.status} />
            </div>
            <div style={{
              fontFamily: 'var(--font-family-mono)',
              fontSize: '0.9rem',
              color: 'var(--deep-obsidian)',
              marginTop: '4px',
              fontWeight: 600
            }}>
              ID: {vehicle.vehicle_identifier}
            </div>
          </div>

          <div style={{ textAlign: 'right', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            <div>Created: {new Date(vehicle.created_at).toLocaleDateString()}</div>
            <div>Last Polled: {new Date(vehicle.updated_at).toLocaleTimeString()}</div>
          </div>
        </div>

        {/* Live telemetry stats row */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '16px',
          marginTop: '24px'
        }}>
          <div style={{ background: 'var(--bg-surface-elevated)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-strong)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              <Gauge size={18} color="#0A0A0A" />
              <span>Speed</span>
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '6px' }}>
              {latest ? `${latest.speed} km/h` : '0.0 km/h'}
            </div>
          </div>

          <div style={{ background: 'var(--bg-surface-elevated)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-strong)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              <Battery size={18} color="#059669" />
              <span>Battery Level</span>
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '6px' }}>
              {latest ? `${latest.battery_level}%` : '—'}
            </div>
          </div>

          <div style={{ background: 'var(--bg-surface-elevated)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-strong)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              <MapPin size={18} color="#0A0A0A" />
              <span>Coordinates</span>
            </div>
            <div style={{ fontSize: '1.2rem', fontWeight: 600, marginTop: '6px', fontFamily: 'var(--font-family-mono)' }}>
              {latest ? `${latest.latitude.toFixed(4)}, ${latest.longitude.toFixed(4)}` : 'No data'}
            </div>
          </div>

          <div style={{ background: 'var(--bg-surface-elevated)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-strong)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              <Clock size={18} color="#0A0A0A" />
              <span>Total Telemetry</span>
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '6px' }}>
              {vehicle.total_telemetry_records} records
            </div>
          </div>
        </div>
      </div>

      {/* Map visualization */}
      {latest && (
        <div className="panel">
          <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#059669', boxShadow: '0 0 6px #059669' }} />
                Real-Time Vehicle Route & Motion
              </h3>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Live vehicle location beacon with active route trail • Chennai Transit Corridor
              </span>
            </div>
            {pathTrail.length > 0 && (
              <span style={{
                fontSize: '0.75rem',
                background: 'var(--bg-surface-subtle)',
                color: 'var(--deep-obsidian)',
                padding: '4px 8px',
                borderRadius: '6px',
                border: '1px solid var(--border-strong)',
                fontWeight: 600
              }}>
                🛤️ {pathTrail.length} Breadcrumbs Recorded
              </span>
            )}
          </div>
          <div className="panel-body" style={{ padding: 0 }}>
            <SimulatedMap
              vehicles={[vehicle]}
              center={[latest.latitude, latest.longitude]}
              zoom={14}
              pathTrail={pathTrail}
              autoFollow={true}
            />
          </div>
        </div>
      )}

      {/* Telemetry History Table */}
      <div className="panel">
        <div className="panel-header">
          <h3 className="panel-title">Historical Telemetry Stream</h3>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Chronological records generated by simulation
          </span>
        </div>

        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Record ID</th>
                <th>Timestamp (UTC)</th>
                <th>Latitude</th>
                <th>Longitude</th>
                <th>Speed (km/h)</th>
                <th>Operational Status</th>
                <th>Power Indicator</th>
              </tr>
            </thead>
            <tbody>
              {!telemetryPage || telemetryPage.items.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                    No telemetry records logged yet for this vehicle.
                  </td>
                </tr>
              ) : (
                telemetryPage.items.map((rec) => (
                  <tr key={rec.id}>
                    <td style={{ fontFamily: 'var(--font-family-mono)', color: 'var(--text-muted)' }}>
                      #{rec.id}
                    </td>
                    <td>{new Date(rec.timestamp).toLocaleString()}</td>
                    <td style={{ fontFamily: 'var(--font-family-mono)' }}>{rec.latitude.toFixed(6)}</td>
                    <td style={{ fontFamily: 'var(--font-family-mono)' }}>{rec.longitude.toFixed(6)}</td>
                    <td><strong>{rec.speed}</strong> km/h</td>
                    <td>
                      <StatusBadge status={rec.status} />
                    </td>
                    <td>{rec.battery_level}%</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Telemetry Pagination */}
        {telemetryPage && telemetryPage.total_pages > 1 && (
          <div style={{
            padding: '14px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderTop: '1px solid var(--border-subtle)',
            fontSize: '0.85rem',
            color: 'var(--text-secondary)'
          }}>
            <div>
              Showing page {page} of {telemetryPage.total_pages} ({telemetryPage.total} total records)
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                className="btn btn-secondary"
                style={{ padding: '4px 10px' }}
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </button>
              <button
                className="btn btn-secondary"
                style={{ padding: '4px 10px' }}
                disabled={page >= telemetryPage.total_pages}
                onClick={() => setPage((p) => Math.min(telemetryPage.total_pages, p + 1))}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
