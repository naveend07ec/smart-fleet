import React, { useState, useEffect } from 'react';
import {
  Shield,
  Lock,
  Unlock,
  Key,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Database,
  ArrowRight,
  RefreshCw,
  FileText,
  Play
} from 'lucide-react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);
import { api } from '../services/api';
import {
  IBEStatus,
  IBECiphertextBundle,
  IBEDecryptResult,
  IBEExperiment,
  Vehicle
} from '../types';
import { MetricCard } from '../components/MetricCard';

export const IbeLabPage: React.FC = () => {
  const [ibeStatus, setIbeStatus] = useState<IBEStatus | null>(null);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loadingStatus, setLoadingStatus] = useState<boolean>(true);

  // Form Inputs
  const [recipientId, setRecipientId] = useState<string>('traffic-control-hub-01');
  const [unauthId, setUnauthId] = useState<string>('unauthorized-adversary-node');
  const [selectedPreset, setSelectedPreset] = useState<string>('preset1');
  const [payloadText, setPayloadText] = useState<string>(() => JSON.stringify({
    vehicle_id: 'SIM-DEMO-001',
    speed: 58.4,
    status: 'moving',
    latitude: 13.0827,
    longitude: 80.2707,
    battery: 82.5,
    timestamp: '2026-10-29T12:00:00Z'
  }, null, 2));

  // Interactive Execution State
  const [encrypting, setEncrypting] = useState<boolean>(false);
  const [decrypting, setDecrypting] = useState<boolean>(false);
  const [ciphertextBundle, setCiphertextBundle] = useState<IBECiphertextBundle | null>(null);
  const [authResult, setAuthResult] = useState<IBEDecryptResult | null>(null);
  const [unauthResult, setUnauthResult] = useState<IBEDecryptResult | null>(null);
  const [tamperResult, setTamperResult] = useState<IBEDecryptResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Experiment History State
  const [experiments, setExperiments] = useState<IBEExperiment[]>([]);
  const [loadingExperiments, setLoadingExperiments] = useState<boolean>(false);
  const [runningExperiment, setRunningExperiment] = useState<boolean>(false);

  const loadInitialData = async () => {
    setLoadingStatus(true);
    try {
      const [statusRes, vehRes, expRes] = await Promise.all([
        api.getIBEStatus(),
        api.getVehicles(1, 15),
        api.getIBEExperiments(1, 10),
      ]);
      setIbeStatus(statusRes);
      setVehicles(vehRes.items);
      setExperiments(expRes.items);
      setErrorMessage(null);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load IBE security lab status');
    } finally {
      setLoadingStatus(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const handlePresetChange = (preset: string) => {
    setSelectedPreset(preset);
    if (preset === 'vehicle' && vehicles.length > 0) {
      const v = vehicles[0];
      setPayloadText(JSON.stringify({
        vehicle_id: v.vehicle_identifier,
        name: v.name,
        status: v.status,
        telemetry: v.latest_telemetry || null
      }, null, 2));
    } else if (preset === 'preset1') {
      setPayloadText(JSON.stringify({
        vehicle_id: 'SIM-DEMO-001',
        speed: 58.4,
        status: 'moving',
        latitude: 13.0827,
        longitude: 80.2707,
        battery: 82.5,
        timestamp: new Date().toISOString()
      }, null, 2));
    } else if (preset === 'preset2') {
      setPayloadText(JSON.stringify({
        alert: 'CRITICAL_BATTERY_DRAIN',
        vehicle_id: 'SIM-DEMO-010',
        diagnostics: { cell_voltage: 3.1, thermal_warning: false },
        emergency_dispatch: true,
        coordinates: [13.0450, 80.1240]
      }, null, 2));
    } else if (preset === 'preset3') {
      setPayloadText(JSON.stringify({
        fleet_report: 'METRO_TRANSIT_HOURLY_SYNC',
        active_units: ['SIM-DEMO-001', 'SIM-DEMO-002', 'SIM-DEMO-003', 'SIM-DEMO-007'],
        avg_fleet_speed_kmh: 48.7,
        total_passengers_simulated: 184,
        telemetry_hash: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08'
      }, null, 2));
    }
  };

  const handleEncryptOnly = async () => {
    setEncrypting(true);
    setErrorMessage(null);
    setAuthResult(null);
    setUnauthResult(null);
    setTamperResult(null);
    try {
      const bundle = await api.encryptIBE(recipientId.trim(), payloadText);
      setCiphertextBundle(bundle);
    } catch (err: any) {
      setErrorMessage(err.message || 'Encryption failed');
    } finally {
      setEncrypting(false);
    }
  };

  const handleTestAuthorized = async () => {
    if (!ciphertextBundle) return;
    setDecrypting(true);
    setErrorMessage(null);
    try {
      const res = await api.decryptIBE(recipientId.trim(), ciphertextBundle);
      setAuthResult(res);
    } catch (err: any) {
      setErrorMessage(err.message || 'Authorized decryption request failed');
    } finally {
      setDecrypting(false);
    }
  };

  const handleTestUnauthorized = async () => {
    if (!ciphertextBundle) return;
    setDecrypting(true);
    setErrorMessage(null);
    try {
      const res = await api.decryptIBE(unauthId.trim(), ciphertextBundle);
      setUnauthResult(res);
    } catch (err: any) {
      setErrorMessage(err.message || 'Unauthorized decryption request failed');
    } finally {
      setDecrypting(false);
    }
  };

  const handleTestTamper = async () => {
    if (!ciphertextBundle) return;
    setDecrypting(true);
    try {
      const tampered = { ...ciphertextBundle };
      // Corrupt the base64 ciphertext
      const origB64 = tampered.ciphertext_b64;
      const flipped = origB64.endsWith('==') ? origB64.slice(0, -2) + 'AA==' : origB64.slice(0, -1) + 'X';
      tampered.ciphertext_b64 = flipped;

      const res = await api.decryptIBE(recipientId.trim(), tampered);
      setTamperResult(res);
    } catch (err: any) {
      setErrorMessage(err.message || 'Tamper test execution error');
    } finally {
      setDecrypting(false);
    }
  };

  const handleRunFullExperiment = async () => {
    setRunningExperiment(true);
    setErrorMessage(null);
    try {
      const exp = await api.createIBEExperiment({
        recipient_identity: recipientId.trim(),
        unauthorized_identity: unauthId.trim(),
        payload: payloadText,
        notes: `Synthetic research trial (${payloadText.length} bytes payload)`
      });

      // Refresh experiments list
      const expRes = await api.getIBEExperiments(1, 10);
      setExperiments(expRes.items);

      // Also update local interactive state with latest run
      await handleEncryptOnly();
    } catch (err: any) {
      setErrorMessage(err.message || 'Full experiment trial failed');
    } finally {
      setRunningExperiment(false);
    }
  };

  // Chart data for experiment timing comparisons
  const validExps = experiments.slice(0, 6).reverse();
  const chartLabels = validExps.map((e) => e.experiment_id.replace('IBE-EXP-', '#'));
  const encTimes = validExps.map((e) => e.encryption_duration_ms);
  const decTimes = validExps.map((e) => e.decryption_duration_ms);

  const experimentChartData = {
    labels: chartLabels.length > 0 ? chartLabels : ['No trials'],
    datasets: [
      {
        label: 'Encryption Time (ms)',
        data: encTimes.length > 0 ? encTimes : [0],
        backgroundColor: '#3b82f6',
      },
      {
        label: 'Decryption Time (ms)',
        data: decTimes.length > 0 ? decTimes : [0],
        backgroundColor: '#10b981',
      },
    ],
  };

  return (
    <div className="page-container" data-testid="ibe-lab-page">
      <div className="minimal-header">
        <div>
          <h1 className="minimal-title">Identity-Based Encryption (IBE) Lab</h1>
          <p className="minimal-subtitle">Pairing-based encryption, PKG private-key derivation, and cross-identity isolation</p>
        </div>
        <div className="minimal-actions">
          <button className="btn btn-secondary" onClick={loadInitialData} disabled={loadingStatus}>
            <RefreshCw size={14} /> Refresh State
          </button>
        </div>
      </div>

      {/* Trust Model & Key Escrow Note */}
      <div style={{
        background: 'var(--bg-surface-elevated)',
        border: '1px solid var(--border-strong)',
        borderRadius: 'var(--radius-md)',
        padding: '16px 20px',
        display: 'flex',
        gap: '14px',
        alignItems: 'flex-start'
      }}>
        <Key size={20} color="var(--deep-obsidian)" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
          <strong style={{ color: 'var(--deep-obsidian)' }}>Boneh-Franklin IBE with PKG Key-Escrow Limitation:</strong>{' '}
          BN128 pairing curve with AES-256-GCM authenticated hybrid encryption. The PKG derives keys from master secret <code>s</code>.
        </div>
      </div>

      {errorMessage && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          padding: '12px 16px',
          borderRadius: '8px',
          color: '#f87171',
          display: 'flex',
          gap: '10px',
          alignItems: 'center'
        }}>
          <AlertTriangle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Top Architecture Status Cards */}
      <div className="metrics-grid">
        <MetricCard
          title="Cryptographic Scheme"
          value="Boneh-Franklin"
          subtext="BN128 Pairing + AES-256-GCM"
          icon={<Shield size={20} color="#3b82f6" />}
        />
        <MetricCard
          title="Pairing Curve"
          value="alt_bn128"
          subtext="254-bit prime field (128-bit security)"
          icon={<Database size={20} color="#06b6d4" />}
        />
        <MetricCard
          title="Public Parameter"
          value="P_pub ∈ G2"
          subtext="Master secret s securely held by PKG"
          icon={<Key size={20} color="#f59e0b" />}
        />
        <MetricCard
          title="Evaluation Trials"
          value={experiments.length}
          subtext="Persisted scientific records"
          icon={<FileText size={20} color="#10b981" />}
        />
      </div>

      {/* Main Interactive Panel */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: '20px' }}>
        {/* Left: Input & Setup */}
        <div className="panel">
          <div className="panel-header">
            <h3 className="panel-title">
              <Lock size={18} color="#60a5fa" />
              <span>Experiment Configuration</span>
            </h3>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Synthetic Telemetry Input
            </span>
          </div>

          <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  Authorized Recipient Identity (Public ID)
                </label>
                <input
                  type="text"
                  className="form-input"
                  style={{ width: '100%', fontFamily: 'var(--font-family-mono)', fontSize: '0.85rem' }}
                  value={recipientId}
                  onChange={(e) => setRecipientId(e.target.value)}
                  placeholder="e.g. traffic-control-hub-01"
                  id="input-recipient-identity"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  Unauthorized Adversary Identity (Test Key)
                </label>
                <input
                  type="text"
                  className="form-input"
                  style={{ width: '100%', fontFamily: 'var(--font-family-mono)', fontSize: '0.85rem' }}
                  value={unauthId}
                  onChange={(e) => setUnauthId(e.target.value)}
                  placeholder="e.g. rogue-vehicle-node"
                  id="input-unauthorized-identity"
                />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                  Payload Preset
                </label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    type="button"
                    className={`btn ${selectedPreset === 'preset1' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '2px 8px', fontSize: '0.75rem' }}
                    onClick={() => handlePresetChange('preset1')}
                  >
                    Standard (128B)
                  </button>
                  <button
                    type="button"
                    className={`btn ${selectedPreset === 'preset2' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '2px 8px', fontSize: '0.75rem' }}
                    onClick={() => handlePresetChange('preset2')}
                  >
                    Alert (256B)
                  </button>
                  <button
                    type="button"
                    className={`btn ${selectedPreset === 'preset3' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '2px 8px', fontSize: '0.75rem' }}
                    onClick={() => handlePresetChange('preset3')}
                  >
                    Fleet Batch (512B)
                  </button>
                </div>
              </div>

              <textarea
                className="form-input"
                style={{
                  width: '100%',
                  height: '140px',
                  fontFamily: 'var(--font-family-mono)',
                  fontSize: '0.82rem',
                  resize: 'vertical'
                }}
                value={payloadText}
                onChange={(e) => setPayloadText(e.target.value)}
                id="textarea-payload"
              />
            </div>

            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <button
                className="btn btn-primary"
                onClick={handleRunFullExperiment}
                disabled={runningExperiment || encrypting}
                id="btn-run-full-experiment"
              >
                <Play size={16} />
                <span>{runningExperiment ? 'Executing Trial...' : 'Run Full Verified Experiment'}</span>
              </button>

              <button
                className="btn btn-secondary"
                onClick={handleEncryptOnly}
                disabled={encrypting || runningExperiment}
                id="btn-encrypt-only"
              >
                <Lock size={14} />
                <span>Encrypt Only</span>
              </button>
            </div>
          </div>
        </div>

        {/* Right: Ciphertext Preview & Decryption Actions */}
        <div className="panel">
          <div className="panel-header">
            <h3 className="panel-title">
              <Key size={18} color="#10b981" />
              <span>Ciphertext & Decryption Tests</span>
            </h3>
            {ciphertextBundle && (
              <span style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600 }}>
                Encrypted in {ciphertextBundle.encryption_duration_ms} ms
              </span>
            )}
          </div>

          <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {!ciphertextBundle ? (
              <div style={{
                padding: '40px 20px',
                textAlign: 'center',
                color: 'var(--text-muted)',
                background: 'var(--bg-surface-elevated)',
                borderRadius: '8px'
              }}>
                <Lock size={32} style={{ margin: '0 auto 10px', opacity: 0.4 }} />
                <div>No active ciphertext. Click "Run Full Verified Experiment" or "Encrypt Only".</div>
              </div>
            ) : (
              <>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                    <span>Ciphertext Preview (AES-GCM Payload + Ephemeral Point U)</span>
                    <span>{ciphertextBundle.ciphertext_size_bytes} bytes</span>
                  </div>
                  <pre style={{
                    background: '#090d16',
                    border: '1px solid var(--border-subtle)',
                    padding: '10px',
                    borderRadius: '6px',
                    fontSize: '0.72rem',
                    fontFamily: 'var(--font-family-mono)',
                    color: '#93c5fd',
                    maxHeight: '90px',
                    overflowY: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all'
                  }}>
                    {ciphertextBundle.ciphertext_b64}
                  </pre>
                </div>

                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                    onClick={handleTestAuthorized}
                    disabled={decrypting}
                  >
                    <Unlock size={14} color="#10b981" />
                    <span>Authorized Decrypt</span>
                  </button>

                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                    onClick={handleTestUnauthorized}
                    disabled={decrypting}
                  >
                    <XCircle size={14} color="#ef4444" />
                    <span>Unauthorized Decrypt</span>
                  </button>

                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                    onClick={handleTestTamper}
                    disabled={decrypting}
                  >
                    <AlertTriangle size={14} color="#f59e0b" />
                    <span>Tamper Check</span>
                  </button>
                </div>

                {/* Outcome Cards */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {authResult && (
                    <div style={{
                      background: authResult.success ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                      border: `1px solid ${authResult.success ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                      padding: '10px 14px',
                      borderRadius: '6px',
                      fontSize: '0.82rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {authResult.success ? <CheckCircle2 size={16} color="#10b981" /> : <XCircle size={16} color="#ef4444" />}
                        <span>Authorized Decryption ({recipientId}): <strong>{authResult.success ? 'VERIFIED MATCH' : 'FAILED'}</strong></span>
                      </div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{authResult.decryption_duration_ms} ms</span>
                    </div>
                  )}

                  {unauthResult && (
                    <div style={{
                      background: !unauthResult.success ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                      border: `1px solid ${!unauthResult.success ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                      padding: '10px 14px',
                      borderRadius: '6px',
                      fontSize: '0.82rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {!unauthResult.success ? <CheckCircle2 size={16} color="#10b981" /> : <XCircle size={16} color="#ef4444" />}
                        <span>Unauthorized Rejection ({unauthId}): <strong>{!unauthResult.success ? 'SECURELY REJECTED' : 'UNEXPECTED SUCCESS'}</strong></span>
                      </div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{unauthResult.decryption_duration_ms} ms</span>
                    </div>
                  )}

                  {tamperResult && (
                    <div style={{
                      background: !tamperResult.success ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                      border: `1px solid ${!tamperResult.success ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                      padding: '10px 14px',
                      borderRadius: '6px',
                      fontSize: '0.82rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {!tamperResult.success ? <CheckCircle2 size={16} color="#10b981" /> : <XCircle size={16} color="#ef4444" />}
                        <span>Tamper Resistance Check: <strong>{!tamperResult.success ? 'INTEGRITY VERIFIED' : 'TAMPER NOT DETECTED'}</strong></span>
                      </div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{tamperResult.decryption_duration_ms} ms</span>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Benchmark Comparisons & Experiment History */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '20px' }}>
        <div className="panel">
          <div className="panel-header">
            <h3 className="panel-title">Timing Performance (ms)</h3>
          </div>
          <div className="panel-body" style={{ height: '260px' }}>
            <Bar
              data={experimentChartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#94a3b8' } } },
                scales: {
                  x: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' } },
                  y: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' }, title: { display: true, text: 'ms', color: '#94a3b8' } },
                },
              }}
            />
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h3 className="panel-title">Persisted IBE Experiment History</h3>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Database records ({experiments.length} total)
            </span>
          </div>

          <div className="table-responsive">
            <table className="custom-table">
              <thead>
                <tr>
                  <th style={{ minWidth: '160px' }}>Experiment ID</th>
                  <th style={{ minWidth: '180px' }}>Recipient ID</th>
                  <th style={{ minWidth: '120px' }}>Payload Size</th>
                  <th style={{ minWidth: '110px' }}>Enc Time</th>
                  <th style={{ minWidth: '110px' }}>Dec Time</th>
                  <th style={{ minWidth: '110px' }}>Authorized</th>
                  <th style={{ minWidth: '120px' }}>Unauthorized</th>
                  <th style={{ minWidth: '130px' }}>Tamper Integrity</th>
                </tr>
              </thead>
              <tbody>
                {experiments.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ textAlign: 'center', padding: '36px 20px', color: 'var(--text-muted)' }}>
                      No experiment trials recorded yet. Run an experiment above to log metrics.
                    </td>
                  </tr>
                ) : (
                  experiments.map((exp) => (
                    <tr key={exp.id}>
                      <td>
                        <code style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--deep-obsidian)', background: 'var(--bg-surface-subtle)', padding: '3px 8px', borderRadius: '6px', border: '1px solid var(--border-strong)' }}>
                          {exp.experiment_id}
                        </code>
                      </td>
                      <td>
                        <span style={{ fontFamily: 'var(--font-family-mono)', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                          {exp.recipient_identity}
                        </span>
                      </td>
                      <td>
                        <strong style={{ fontSize: '0.84rem', color: 'var(--deep-obsidian)' }}>
                          {exp.payload_size_bytes.toLocaleString()} B
                        </strong>
                      </td>
                      <td>
                        <span style={{ fontFamily: 'var(--font-family-mono)', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                          {exp.encryption_duration_ms > 0 ? `${Number(exp.encryption_duration_ms).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} ms` : '—'}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontFamily: 'var(--font-family-mono)', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                          {exp.decryption_duration_ms > 0 ? `${Number(exp.decryption_duration_ms).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} ms` : '—'}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontSize: '0.72rem', padding: '3px 8px', borderRadius: 'var(--radius-full)', fontWeight: 700, background: exp.authorized_success ? 'rgba(5, 150, 105, 0.08)' : 'rgba(220, 38, 38, 0.08)', color: exp.authorized_success ? '#059669' : '#DC2626', border: `1px solid ${exp.authorized_success ? 'rgba(5, 150, 105, 0.25)' : 'rgba(220, 38, 38, 0.25)'}` }}>
                          {exp.authorized_success ? '✓ Match' : '✗ Failed'}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontSize: '0.72rem', padding: '3px 8px', borderRadius: 'var(--radius-full)', fontWeight: 700, background: exp.unauthorized_rejected ? 'rgba(5, 150, 105, 0.08)' : 'rgba(220, 38, 38, 0.08)', color: exp.unauthorized_rejected ? '#059669' : '#DC2626', border: `1px solid ${exp.unauthorized_rejected ? 'rgba(5, 150, 105, 0.25)' : 'rgba(220, 38, 38, 0.25)'}` }}>
                          {exp.unauthorized_rejected ? '✓ Blocked' : '✗ Leaked'}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontSize: '0.72rem', padding: '3px 8px', borderRadius: 'var(--radius-full)', fontWeight: 700, background: exp.tamper_check_passed ? 'rgba(5, 150, 105, 0.08)' : 'rgba(220, 38, 38, 0.08)', color: exp.tamper_check_passed ? '#059669' : '#DC2626', border: `1px solid ${exp.tamper_check_passed ? 'rgba(5, 150, 105, 0.25)' : 'rgba(220, 38, 38, 0.25)'}` }}>
                          {exp.tamper_check_passed ? '✓ Valid' : '✗ Failed'}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
