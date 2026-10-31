import React, { useEffect, useState } from 'react';
import { Search, Plus, Eye, Edit2, Trash2, RefreshCw, AlertTriangle } from 'lucide-react';
import { api } from '../services/api';
import { Vehicle, VehicleCreatePayload, VehicleUpdatePayload } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { VehicleModal } from '../components/VehicleModal';

interface VehiclesPageProps {
  onViewVehicle: (id: number) => void;
}

export const VehiclesPage: React.FC<VehiclesPageProps> = ({ onViewVehicle }) => {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [vehicleToEdit, setVehicleToEdit] = useState<Vehicle | null>(null);

  const fetchFleet = async () => {
    setLoading(true);
    try {
      const data = await api.getVehicles(page, limit, search, statusFilter);
      setVehicles(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch vehicles');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFleet();
  }, [page, statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchFleet();
  };

  const handleCreateSubmit = async (payload: VehicleCreatePayload) => {
    await api.createVehicle(payload);
    fetchFleet();
  };

  const handleUpdateSubmit = async (id: number, payload: VehicleUpdatePayload) => {
    await api.updateVehicle(id, payload);
    fetchFleet();
  };

  const handleDelete = async (v: Vehicle) => {
    if (window.confirm(`Are you sure you want to delete simulated vehicle "${v.name}" (${v.vehicle_identifier})?`)) {
      try {
        await api.deleteVehicle(v.id);
        fetchFleet();
      } catch (err: any) {
        alert(err.message || 'Failed to delete vehicle');
      }
    }
  };

  return (
    <div className="page-container" data-testid="vehicles-page">
      <div className="minimal-header">
        <div>
          <h1 className="minimal-title">Vehicle Fleet</h1>
          <p className="minimal-subtitle">Manage registered vehicles, status and telemetry</p>
        </div>
        <div className="minimal-actions">
          <button className="btn btn-secondary" onClick={fetchFleet}>
            <RefreshCw size={14} /> Refresh
          </button>
          <button
            className="btn btn-primary"
            onClick={() => {
              setVehicleToEdit(null);
              setModalOpen(true);
            }}
            id="btn-register-vehicle"
          >
            <Plus size={16} /> Register Vehicle
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="panel" style={{ padding: '16px 20px' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: '240px' }}>
            <Search size={16} style={{ position: 'absolute', left: 12, top: 11, color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search by vehicle ID or name..."
              className="form-input"
              style={{ width: '100%', paddingLeft: '36px' }}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              id="search-vehicles-input"
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Status:</span>
            <select
              className="form-select"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              id="filter-status-select"
            >
              <option value="all">All Statuses</option>
              <option value="moving">Moving</option>
              <option value="idle">Idle</option>
              <option value="offline">Offline</option>
            </select>
          </div>

          <button type="submit" className="btn btn-secondary">
            Apply Filter
          </button>
        </form>
      </div>

      {error && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          padding: '14px',
          borderRadius: '8px',
          color: '#f87171',
          display: 'flex',
          gap: '10px',
          alignItems: 'center'
        }}>
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Fleet Table */}
      <div className="panel">
        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Vehicle Identifier</th>
                <th>Fleet Name</th>
                <th>Simulated Status</th>
                <th>Speed (km/h)</th>
                <th>Power Indicator</th>
                <th>Coordinates (Simulated)</th>
                <th>Last Update</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '40px' }}>
                    <div className="spinner" style={{ margin: '0 auto 10px' }} />
                    <span style={{ color: 'var(--text-muted)' }}>Loading fleet records...</span>
                  </td>
                </tr>
              ) : vehicles.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '40px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>
                      No vehicles found matching the filter criteria.
                    </span>
                  </td>
                </tr>
              ) : (
                vehicles.map((v) => {
                  const tel = v.latest_telemetry;
                  const speed = tel ? `${tel.speed} km/h` : '—';
                  const batt = tel ? `${tel.battery_level}%` : '—';
                  const coords = tel ? `${tel.latitude.toFixed(4)}, ${tel.longitude.toFixed(4)}` : 'No telemetry';
                  const updated = tel ? new Date(tel.timestamp).toLocaleTimeString() : new Date(v.updated_at).toLocaleTimeString();

                  return (
                    <tr key={v.id} data-testid={`vehicle-row-${v.id}`}>
                      <td>
                        <strong style={{ fontFamily: 'var(--font-family-mono)', color: 'var(--deep-obsidian)' }}>
                          {v.vehicle_identifier}
                        </strong>
                      </td>
                      <td>{v.name}</td>
                      <td>
                        <StatusBadge status={v.status} />
                      </td>
                      <td>{speed}</td>
                      <td>
                        <div className="battery-wrapper">
                          <div className="battery-bar">
                            <div
                              className="battery-fill"
                              style={{
                                width: `${tel?.battery_level || 0}%`,
                                backgroundColor: (tel?.battery_level || 0) > 30 ? '#10b981' : '#ef4444',
                              }}
                            />
                          </div>
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{batt}</span>
                        </div>
                      </td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{coords}</td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{updated}</td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '6px' }}>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '6px 10px' }}
                            onClick={() => onViewVehicle(v.id)}
                            title="View Details"
                            id={`btn-view-${v.id}`}
                          >
                            <Eye size={14} />
                          </button>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '6px 10px' }}
                            onClick={() => {
                              setVehicleToEdit(v);
                              setModalOpen(true);
                            }}
                            title="Edit Vehicle"
                            id={`btn-edit-${v.id}`}
                          >
                            <Edit2 size={14} />
                          </button>
                          <button
                            className="btn btn-danger"
                            style={{ padding: '6px 10px' }}
                            onClick={() => handleDelete(v)}
                            title="Delete Vehicle"
                            id={`btn-delete-${v.id}`}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination footer */}
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
            Showing {vehicles.length > 0 ? (page - 1) * limit + 1 : 0} -{' '}
            {Math.min(page * limit, total)} of {total} vehicles
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
            <span style={{ alignSelf: 'center', padding: '0 8px' }}>
              Page {page} of {totalPages}
            </span>
            <button
              className="btn btn-secondary"
              style={{ padding: '4px 10px' }}
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              Next
            </button>
          </div>
        </div>
      </div>

      <VehicleModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmitCreate={handleCreateSubmit}
        onSubmitUpdate={handleUpdateSubmit}
        vehicleToEdit={vehicleToEdit}
      />
    </div>
  );
};
