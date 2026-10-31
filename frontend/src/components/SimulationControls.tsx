import React, { useState } from 'react';
import { Play, Square, Settings, RefreshCw, AlertTriangle, ShieldCheck } from 'lucide-react';
import { SimulationStatus, SimulationStartParams } from '../types';

interface SimulationControlsProps {
  status: SimulationStatus | null;
  onStart: (params: SimulationStartParams) => Promise<void>;
  onStop: () => Promise<void>;
  loading: boolean;
}

export const SimulationControls: React.FC<SimulationControlsProps> = ({
  status,
  onStart,
  onStop,
  loading
}) => {
  const [vehicleCount, setVehicleCount] = useState<number>(25);
  const [intervalSeconds, setIntervalSeconds] = useState<number>(3.0);
  const [randomSeed, setRandomSeed] = useState<string>('');
  const [actionError, setActionError] = useState<string | null>(null);

  const handleStart = async () => {
    setActionError(null);
    try {
      const seedNum = randomSeed.trim() !== '' ? parseInt(randomSeed.trim(), 10) : undefined;
      await onStart({
        vehicle_count: vehicleCount,
        interval_seconds: intervalSeconds,
        random_seed: Number.isNaN(seedNum) ? undefined : seedNum,
      });
    } catch (err: any) {
      setActionError(err.message || 'Failed to start simulation');
    }
  };

  const handleStop = async () => {
    setActionError(null);
    try {
      await onStop();
    } catch (err: any) {
      setActionError(err.message || 'Failed to stop simulation');
    }
  };

  const isRunning = status?.is_running ?? false;

  return (
    <div className="panel" data-testid="simulation-controls-panel">
      <div className="panel-header">
        <h2 className="panel-title">
          <img src="/logo.png" alt="SmartFleet Logo" style={{ height: '22px', width: 'auto', objectFit: 'contain' }} />
          <span>Telemetry Simulation Engine</span>
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.8rem',
            padding: '4px 10px',
            borderRadius: '999px',
            background: isRunning ? 'rgba(16, 185, 129, 0.2)' : 'rgba(100, 116, 139, 0.2)',
            color: isRunning ? '#34d399' : '#94a3b8',
            fontWeight: 600
          }}>
            <span style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: isRunning ? '#10b981' : '#64748b'
            }} />
            {isRunning ? 'RUNNING' : 'STOPPED'}
          </span>
        </div>
      </div>

      <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Notice on simulation separation & hosted deployment access protection */}
        <div style={{
          background: 'rgba(59, 130, 246, 0.08)',
          border: '1px solid rgba(59, 130, 246, 0.25)',
          borderRadius: '8px',
          padding: '12px 16px',
          fontSize: '0.85rem',
          color: '#bfdbfe',
          display: 'flex',
          gap: '12px',
          alignItems: 'flex-start'
        }}>
          <ShieldCheck size={20} style={{ flexShrink: 0, marginTop: '2px', color: '#60a5fa' }} />
          <div>
            <strong>Architecture Notice:</strong> Simulation controls and vehicle modifications are separated from the public read-only views. In public production deployments, reverse-proxy access control or API tokens should restrict this panel.
          </div>
        </div>

        {actionError && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '8px',
            padding: '12px 16px',
            fontSize: '0.85rem',
            color: '#fca5a5',
            display: 'flex',
            gap: '10px',
            alignItems: 'center'
          }}>
            <AlertTriangle size={18} />
            <span>{actionError}</span>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
              Fleet Size Scenario
            </label>
            <select
              className="form-select"
              style={{ width: '100%' }}
              value={vehicleCount}
              onChange={(e) => setVehicleCount(Number(e.target.value))}
              disabled={isRunning || loading}
              id="select-fleet-scenario"
            >
              <option value={10}>10 Vehicles (Small Scenario)</option>
              <option value={25}>25 Vehicles (Standard Scenario)</option>
              <option value={50}>50 Vehicles (Large Fleet Scenario)</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
              Telemetry Frequency (Seconds)
            </label>
            <input
              type="number"
              step="0.5"
              min="0.5"
              max="30"
              className="form-input"
              style={{ width: '100%' }}
              value={intervalSeconds}
              onChange={(e) => setIntervalSeconds(Number(e.target.value))}
              disabled={isRunning || loading}
              id="input-sim-interval"
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
              Deterministic Seed (Optional)
            </label>
            <input
              type="number"
              placeholder="e.g. 42 (Repeatable)"
              className="form-input"
              style={{ width: '100%' }}
              value={randomSeed}
              onChange={(e) => setRandomSeed(e.target.value)}
              disabled={isRunning || loading}
              id="input-random-seed"
            />
          </div>
        </div>

        {/* Engine status indicators */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: '12px',
          background: 'var(--bg-surface-elevated)',
          padding: '14px',
          borderRadius: '8px',
          fontSize: '0.82rem'
        }}>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Configured Fleet:</span>{' '}
            <strong style={{ color: '#fff' }}>{status?.vehicle_count ?? 0} units</strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Ticks Generated:</span>{' '}
            <strong style={{ color: '#fff' }}>{status?.tick_count ?? 0}</strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Interval:</span>{' '}
            <strong style={{ color: '#fff' }}>{status?.interval_seconds ?? 3}s</strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Deterministic Seed:</span>{' '}
            <strong style={{ color: '#fff' }}>{status?.random_seed !== null && status?.random_seed !== undefined ? status.random_seed : 'Random'}</strong>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {!isRunning ? (
            <button
              className="btn btn-primary"
              onClick={handleStart}
              disabled={loading}
              id="btn-start-simulation"
            >
              <Play size={16} />
              <span>Start Simulation</span>
            </button>
          ) : (
            <button
              className="btn btn-danger"
              onClick={handleStop}
              disabled={loading}
              id="btn-stop-simulation"
            >
              <Square size={16} />
              <span>Stop Simulation</span>
            </button>
          )}

          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {status?.message || 'Ready to produce simulated IoT telemetry.'}
          </div>
        </div>
      </div>
    </div>
  );
};
