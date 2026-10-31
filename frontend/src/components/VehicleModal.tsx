import React, { useState, useEffect } from 'react';
import { X, AlertCircle } from 'lucide-react';
import { Vehicle, VehicleCreatePayload, VehicleUpdatePayload } from '../types';

interface VehicleModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmitCreate?: (payload: VehicleCreatePayload) => Promise<void>;
  onSubmitUpdate?: (id: number, payload: VehicleUpdatePayload) => Promise<void>;
  vehicleToEdit?: Vehicle | null;
}

export const VehicleModal: React.FC<VehicleModalProps> = ({
  isOpen,
  onClose,
  onSubmitCreate,
  onSubmitUpdate,
  vehicleToEdit
}) => {
  const isEditing = Boolean(vehicleToEdit);

  const [identifier, setIdentifier] = useState('');
  const [name, setName] = useState('');
  const [status, setStatus] = useState<'moving' | 'idle' | 'offline'>('idle');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (vehicleToEdit) {
      setIdentifier(vehicleToEdit.vehicle_identifier);
      setName(vehicleToEdit.name);
      setStatus(vehicleToEdit.status);
    } else {
      setIdentifier(`SIM-VEH-${Math.floor(100 + Math.random() * 900)}`);
      setName('');
      setStatus('idle');
    }
    setError(null);
  }, [vehicleToEdit, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('Please provide a vehicle display name.');
      return;
    }
    if (!identifier.trim()) {
      setError('Please provide a vehicle identifier.');
      return;
    }

    setSubmitting(true);
    try {
      if (isEditing && vehicleToEdit && onSubmitUpdate) {
        await onSubmitUpdate(vehicleToEdit.id, {
          name: name.trim(),
          status,
        });
      } else if (onSubmitCreate) {
        await onSubmitCreate({
          vehicle_identifier: identifier.trim(),
          name: name.trim(),
          status,
        });
      }
      onClose();
    } catch (err: any) {
      setError(err.message || 'Operation failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <img src="/logo.png" alt="SmartFleet Logo" style={{ height: '22px', width: 'auto', objectFit: 'contain' }} />
            <h2 style={{ fontSize: '1.05rem', fontWeight: 600 }}>
              {isEditing ? `Edit Vehicle (${vehicleToEdit?.vehicle_identifier})` : 'Register Vehicle'}
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div style={{
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                padding: '10px 14px',
                borderRadius: '6px',
                color: '#f87171',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Vehicle Identifier (Simulated ID)
              </label>
              <input
                type="text"
                className="form-input"
                style={{ width: '100%' }}
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                disabled={isEditing || submitting}
                placeholder="e.g. SIM-VEH-055"
                id="modal-vehicle-identifier"
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
                Unique synthetic fleet tag. Cannot represent real GPS hardware.
              </span>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Display / Fleet Name
              </label>
              <input
                type="text"
                className="form-input"
                style={{ width: '100%' }}
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={submitting}
                placeholder="e.g. Metro Express Shuttle 4"
                id="modal-vehicle-name"
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Initial Simulated Status
              </label>
              <select
                className="form-select"
                style={{ width: '100%' }}
                value={status}
                onChange={(e) => setStatus(e.target.value as any)}
                disabled={submitting}
                id="modal-vehicle-status"
              >
                <option value="moving">moving</option>
                <option value="idle">idle</option>
                <option value="offline">offline</option>
              </select>
            </div>
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting}
              id="modal-submit-btn"
            >
              {submitting ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Vehicle'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
