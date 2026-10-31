import React, { useState, useEffect } from 'react';
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  Lock,
  Unlock,
  Radio,
  Clock,
  Database,
  ArrowRight,
  RefreshCw,
  Play,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileText,
  Copy,
  Info,
  Layers,
  Zap,
  Repeat
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
  SecureTransmission,
  TransmissionAnalytics,
  ExperimentRunPayload,
  ExperimentRunResult
} from '../types';
import { MetricCard } from '../components/MetricCard';

export const SecureTransmissionLabPage: React.FC = () => {
  // State
  const [analytics, setAnalytics] = useState<TransmissionAnalytics | null>(null);
  const [transmissions, setTransmissions] = useState<SecureTransmission[]>([]);
  const [totalRecords, setTotalRecords] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [activeFilter, setActiveFilter] = useState<'all' | 'plaintext' | 'ibe_protected' | 'rejected'>('all');
  const [selectedTx, setSelectedTx] = useState<SecureTransmission | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Experiment Runner Form
  const [vehicleCount, setVehicleCount] = useState<number>(5);
  const [messagesPerVehicle, setMessagesPerVehicle] = useState<number>(3);
  const [runMode, setRunMode] = useState<'both' | 'ibe_protected' | 'plaintext'>('both');
  const [payloadScale, setPayloadScale] = useState<'small' | 'medium' | 'large'>('medium');
  const [experimentRunning, setExperimentRunning] = useState<boolean>(false);
  const [lastBatchResult, setLastBatchResult] = useState<ExperimentRunResult | null>(null);

  // Security Demonstration Suite
  const [demoLoading, setDemoLoading] = useState<boolean>(false);
  const [lastDemoResult, setLastDemoResult] = useState<SecureTransmission | null>(null);
  const [activeScenario, setActiveScenario] = useState<string | null>(null);

  const fetchData = async (page: number = 1, filter: string = activeFilter) => {
    setLoading(true);
    try {
      const modeParam = filter === 'plaintext' || filter === 'ibe_protected' ? filter : undefined;
      const statusParam = filter === 'rejected' ? 'rejected' : undefined;

      const [analyticsData, listData] = await Promise.all([
        api.getTransmissionAnalytics(),
        api.getTransmissionExperiments(page, 15, modeParam, statusParam)
      ]);

      setAnalytics(analyticsData);
      setTransmissions(listData.items || []);
      setTotalRecords(listData.total || 0);
    } catch (err) {
      console.error('Failed to load transmission lab data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(currentPage, activeFilter);
  }, [currentPage, activeFilter]);

  const handleRunExperiment = async () => {
    setExperimentRunning(true);
    try {
      const payload: ExperimentRunPayload = {
        vehicle_count: vehicleCount,
        messages_per_vehicle: messagesPerVehicle,
        mode: runMode,
        payload_category: payloadScale,
        notes: `Frontend trial: ${vehicleCount} veh x ${messagesPerVehicle} msgs (${payloadScale})`
      };
      const result: ExperimentRunResult = await api.runTransmissionExperiment(payload);
      setLastBatchResult(result);
      await fetchData(1, activeFilter);
      setCurrentPage(1);
    } catch (err: any) {
      alert(`Experiment run failed: ${err.message}`);
    } finally {
      setExperimentRunning(false);
    }
  };

  const handleRunSecurityDemo = async (scenario: string) => {
    setDemoLoading(true);
    setActiveScenario(scenario);
    try {
      const res = await api.runSecurityDemonstration(scenario, 'SIM-VEH-001');
      setLastDemoResult(res);
      await fetchData(1, activeFilter);
    } catch (err: any) {
      alert(`Security demo failed: ${err.message}`);
    } finally {
      setDemoLoading(false);
    }
  };

  // Prepare Comparative Charts
  const latencyChartData = {
    labels: ['Conventional Baseline (Mode A)', 'IBE Protected Total (Mode B)', 'IBE Encryption (Client)', 'IBE Decryption (Server)'],
    datasets: [
      {
        label: 'Latency (Milliseconds)',
        data: [
          analytics?.median_plaintext_latency_ms || 1.2,
          analytics?.median_protected_latency_ms || 85.0,
          analytics?.median_encryption_latency_ms || 42.0,
          analytics?.median_decryption_latency_ms || 41.5
        ],
        backgroundColor: [
          'rgba(59, 130, 246, 0.75)',
          'rgba(212, 175, 55, 0.85)',
          'rgba(16, 185, 129, 0.85)',
          'rgba(243, 229, 171, 0.75)',
          'rgba(161, 161, 166, 0.75)'
        ],
        borderColor: [
          '#D4AF37',
          '#10B981',
          '#F3E5AB',
          '#A1A1A6'
        ],
        borderWidth: 1.5,
        borderRadius: 6
      }
    ]
  };

  const overheadChartData = {
    labels: ['Small Payload (~150B)', 'Medium Payload (~450B)', 'Large Payload (~1.5KB)'],
    datasets: [
      {
        label: 'Raw Payload (Bytes)',
        data: [
          analytics?.by_payload_category?.small?.mean_original_bytes || 155,
          analytics?.by_payload_category?.medium?.mean_original_bytes || 445,
          analytics?.by_payload_category?.large?.mean_original_bytes || 1480
        ],
        backgroundColor: 'rgba(161, 161, 166, 0.45)',
        borderColor: '#A1A1A6',
        borderWidth: 1
      },
      {
        label: 'Encrypted Envelope (Bytes)',
        data: [
          analytics?.by_payload_category?.small?.mean_envelope_bytes || 1420,
          analytics?.by_payload_category?.medium?.mean_envelope_bytes || 1850,
          analytics?.by_payload_category?.large?.mean_envelope_bytes || 3250
        ],
        backgroundColor: 'rgba(212, 175, 55, 0.55)',
        borderColor: '#D4AF37',
        borderWidth: 1
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: '#475569',
          font: { family: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif', size: 11 }
        }
      },
      tooltip: {
        backgroundColor: '#0A0A0A',
        titleColor: '#FFFFFF',
        bodyColor: '#E2E8F0',
        borderColor: '#E2E8F0',
        borderWidth: 1
      }
    },
    scales: {
      x: {
        ticks: { color: '#64748B', font: { size: 11 } },
        grid: { color: 'rgba(0, 0, 0, 0.05)' }
      },
      y: {
        ticks: { color: '#64748B', font: { size: 11 } },
        grid: { color: 'rgba(0, 0, 0, 0.05)' }
      }
    }
  };

  return (
    <div className="page-container">
      {/* Header */}
      {/* Minimalist Header */}
      <div className="minimal-header">
        <div>
          <h1 className="minimal-title" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Shield size={24} />
            Secure Vehicle-to-Server Transmission Lab
          </h1>
          <p className="minimal-subtitle">
            Confidentiality, AAD authentication, replay resistance, and cryptographic latency benchmarking
          </p>
        </div>

        <div className="minimal-actions">
          <button
            className="btn btn-secondary"
            onClick={() => fetchData(currentPage, activeFilter)}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', marginTop: '16px' }}>
        <MetricCard
          title="Total Evaluated Transmissions"
          value={analytics?.total_transmissions || 0}
          subtext={`${analytics?.plaintext_transmissions || 0} Baseline • ${analytics?.protected_transmissions || 0} Protected`}
          icon={<Radio size={20} />}
        />
        <MetricCard
          title="Baseline Latency (Mode A)"
          value={`${analytics?.median_plaintext_latency_ms || 0} ms`}
          subtext="Unencrypted JSON HTTP round-trip"
          icon={<Zap size={20} />}
        />
        <MetricCard
          title="IBE Protected Latency (Mode B)"
          value={`${analytics?.median_protected_latency_ms || 0} ms`}
          subtext={`Enc: ${analytics?.median_encryption_latency_ms || 0}ms • Dec: ${analytics?.median_decryption_latency_ms || 0}ms`}
          icon={<Lock size={20} />}
        />
        <MetricCard
          title="Payload Expansion Overhead"
          value={`+${analytics?.mean_payload_expansion_bytes || 0} B`}
          subtext={`Average +${analytics?.mean_payload_expansion_percent || 0}% framing overhead`}
          icon={<Layers size={20} />}
        />
        <MetricCard
          title="Replay & Attack Rejections"
          value={analytics?.rejected_transmissions || 0}
          subtext={`${analytics?.tampering_detected_count || 0} Tampered • ${analytics?.replay_detected_count || 0} Replayed • ${analytics?.unauthorized_identity_count || 0} Unauth`}
          icon={<ShieldAlert size={20} />}
        />
      </div>

      {/* Section 1: Security Demonstration Suite */}
      <div className="panel" style={{ marginTop: '24px' }}>
        <div className="panel-body">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px', flexWrap: 'wrap', gap: '8px' }}>
            <div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--deep-obsidian)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ display: 'inline-flex', padding: '5px', borderRadius: '8px', background: 'rgba(5, 150, 105, 0.08)', color: '#059669' }}>
                  <ShieldCheck size={18} />
                </span>
                Controlled Security Demonstration & Attack Verification
              </h3>
              <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                Execute live attack vectors against the telemetry receiver to empirically verify cryptographic integrity, AAD binding, and replay detection.
              </p>
            </div>
          </div>

          <div className="security-demo-grid">
            {/* Action 1 */}
            <div className="security-demo-card">
              <div>
                <div className="security-card-top">
                  <span className="security-card-pill authorized">Baseline (Mode B)</span>
                  <div className="security-card-icon-halo authorized">
                    <CheckCircle2 size={16} />
                  </div>
                </div>
                <h4 className="security-card-title">1. Authorized Transmission</h4>
                <p className="security-card-desc">
                  Enrolled vehicle transmits authentic IBE-KEM + AES-256-GCM envelope with bound AAD.
                </p>
              </div>
              <button
                className="security-btn-authorized"
                onClick={() => handleRunSecurityDemo('valid_authorized')}
                disabled={demoLoading}
              >
                <Play size={13} />
                <span>{demoLoading && activeScenario === 'valid_authorized' ? 'Transmitting...' : 'Run Authorized Test'}</span>
              </button>
            </div>

            {/* Action 2 */}
            <div className="security-demo-card">
              <div>
                <div className="security-card-top">
                  <span className="security-card-pill attack">Identity Attack</span>
                  <div className="security-card-icon-halo attack">
                    <XCircle size={16} />
                  </div>
                </div>
                <h4 className="security-card-title">2. Rogue / Unenrolled Identity</h4>
                <p className="security-card-desc">
                  Unenrolled adversary node attempts to push telemetry into fleet receiver.
                </p>
              </div>
              <button
                className="security-btn-attack"
                onClick={() => handleRunSecurityDemo('unauthorized_identity')}
                disabled={demoLoading}
              >
                <ShieldAlert size={14} style={{ color: '#DC2626' }} />
                <span>{demoLoading && activeScenario === 'unauthorized_identity' ? 'Simulating Attack...' : 'Simulate Rogue ID Attack'}</span>
              </button>
            </div>

            {/* Action 3 */}
            <div className="security-demo-card">
              <div>
                <div className="security-card-top">
                  <span className="security-card-pill tamper">Ciphertext Tamper</span>
                  <div className="security-card-icon-halo tamper">
                    <AlertTriangle size={16} />
                  </div>
                </div>
                <h4 className="security-card-title">3. Tampered Ciphertext Body</h4>
                <p className="security-card-desc">
                  Flips 1 byte in the transmission ciphertext in-transit. Must fail AEAD tag check.
                </p>
              </div>
              <button
                className="security-btn-attack"
                onClick={() => handleRunSecurityDemo('tampered_ciphertext')}
                disabled={demoLoading}
              >
                <AlertTriangle size={14} style={{ color: '#D97706' }} />
                <span>{demoLoading && activeScenario === 'tampered_ciphertext' ? 'Tampering...' : 'Simulate Ciphertext Tamper'}</span>
              </button>
            </div>

            {/* Action 4 */}
            <div className="security-demo-card">
              <div>
                <div className="security-card-top">
                  <span className="security-card-pill tamper">Tag Corruption</span>
                  <div className="security-card-icon-halo tamper">
                    <AlertTriangle size={16} />
                  </div>
                </div>
                <h4 className="security-card-title">4. Tampered Authentication Tag</h4>
                <p className="security-card-desc">
                  Corrupts the 16-byte AES-GCM GHASH tag. Must reject without leaking payload.
                </p>
              </div>
              <button
                className="security-btn-attack"
                onClick={() => handleRunSecurityDemo('tampered_tag')}
                disabled={demoLoading}
              >
                <AlertTriangle size={14} style={{ color: '#D97706' }} />
                <span>{demoLoading && activeScenario === 'tampered_tag' ? 'Tampering...' : 'Simulate Tag Tamper'}</span>
              </button>
            </div>

            {/* Action 5 */}
            <div className="security-demo-card">
              <div>
                <div className="security-card-top">
                  <span className="security-card-pill replay">Replay Vector</span>
                  <div className="security-card-icon-halo replay">
                    <Repeat size={16} />
                  </div>
                </div>
                <h4 className="security-card-title">5. Replay Attack Resubmission</h4>
                <p className="security-card-desc">
                  Re-transmits identical captured valid ciphertext bundle. Must fail replay window.
                </p>
              </div>
              <button
                className="security-btn-attack"
                onClick={() => handleRunSecurityDemo('replay_attack')}
                disabled={demoLoading}
              >
                <Repeat size={14} style={{ color: '#4F46E5' }} />
                <span>{demoLoading && activeScenario === 'replay_attack' ? 'Replaying...' : 'Simulate Replay Attack'}</span>
              </button>
            </div>

            {/* Action 6 */}
            <div className="security-demo-card">
              <div>
                <div className="security-card-top">
                  <span className="security-card-pill attack">Identity Substitution</span>
                  <div className="security-card-icon-halo attack">
                    <XCircle size={16} />
                  </div>
                </div>
                <h4 className="security-card-title">6. Cross-Vehicle Substitution</h4>
                <p className="security-card-desc">
                  Vehicle A sends valid telemetry claiming in headers to be Vehicle B.
                </p>
              </div>
              <button
                className="security-btn-attack"
                onClick={() => handleRunSecurityDemo('cross_vehicle_substitution')}
                disabled={demoLoading}
              >
                <ShieldAlert size={14} style={{ color: '#DC2626' }} />
                <span>{demoLoading && activeScenario === 'cross_vehicle_substitution' ? 'Testing...' : 'Simulate Identity Substitution'}</span>
              </button>
            </div>

            {/* Action 7: Critical Phase 3.1 Impersonation */}
            <div className="security-demo-card">
              <div>
                <div className="security-card-top">
                  <span className="security-card-pill attack">Impersonation</span>
                  <div className="security-card-icon-halo attack">
                    <ShieldAlert size={16} />
                  </div>
                </div>
                <h4 className="security-card-title">7. Attacker Impersonation Attack</h4>
                <p className="security-card-desc">
                  Adversary crafts fresh envelope with server public key claiming enrolled Vehicle A, but lacks Ed25519 signing key.
                </p>
              </div>
              <button
                className="security-btn-attack"
                onClick={() => handleRunSecurityDemo('attacker_impersonation')}
                disabled={demoLoading}
              >
                <ShieldAlert size={14} style={{ color: '#DC2626' }} />
                <span>{demoLoading && activeScenario === 'attacker_impersonation' ? 'Attacking...' : 'Simulate Genuine Impersonation'}</span>
              </button>
            </div>

            {/* Action 8: Tampered Signature */}
            <div className="security-demo-card">
              <div>
                <div className="security-card-top">
                  <span className="security-card-pill tamper">Signature Tamper</span>
                  <div className="security-card-icon-halo tamper">
                    <Lock size={16} />
                  </div>
                </div>
                <h4 className="security-card-title">8. Tampered Vehicle Signature</h4>
                <p className="security-card-desc">
                  Corrupts 1 byte of the vehicle's Ed25519 digital signature. Rejected before decryption.
                </p>
              </div>
              <button
                className="security-btn-attack"
                onClick={() => handleRunSecurityDemo('tampered_signature')}
                disabled={demoLoading}
              >
                <Lock size={14} style={{ color: '#D97706' }} />
                <span>{demoLoading && activeScenario === 'tampered_signature' ? 'Tampering...' : 'Simulate Signature Tamper'}</span>
              </button>
            </div>
          </div>

          {/* Real-time Demonstration Result Banner */}
          {lastDemoResult && (
            <div
              style={{
                marginTop: '20px',
                padding: '16px 20px',
                borderRadius: '12px',
                background: lastDemoResult.status === 'success' ? 'rgba(5, 150, 105, 0.05)' : 'rgba(220, 38, 38, 0.05)',
                border: `1px solid ${lastDemoResult.status === 'success' ? 'rgba(5, 150, 105, 0.25)' : 'rgba(220, 38, 38, 0.25)'}`
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  {lastDemoResult.status === 'success' ? (
                    <CheckCircle2 size={24} style={{ color: '#059669' }} />
                  ) : (
                    <ShieldAlert size={24} style={{ color: '#DC2626' }} />
                  )}
                  <div>
                    <strong style={{ fontSize: '0.94rem', color: lastDemoResult.status === 'success' ? '#065F46' : '#991B1B' }}>
                      {lastDemoResult.status === 'success' ? 'Transmission Accepted & Telemetry Persisted' : 'Security Guard Rejection Triggered (Expected)'}
                    </strong>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '3px' }}>
                      <strong>Transmission ID:</strong> <code style={{ color: 'var(--deep-obsidian)' }}>{lastDemoResult.transmission_id}</code> • <strong>Status:</strong> {lastDemoResult.status.toUpperCase()}
                    </div>
                  </div>
                </div>

                <div style={{ textAlign: 'right', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                  <div>Total Processing: <strong style={{ color: 'var(--deep-obsidian)' }}>{lastDemoResult.total_duration_ms} ms</strong></div>
                  <div>Envelope Size: <strong style={{ color: 'var(--deep-obsidian)' }}>{lastDemoResult.encrypted_envelope_size_bytes} B</strong></div>
                </div>
              </div>

              {lastDemoResult.rejection_reason && (
                <div style={{ marginTop: '10px', fontSize: '0.82rem', padding: '8px 12px', background: 'var(--base-white)', border: '1px solid rgba(220, 38, 38, 0.2)', borderRadius: '6px', color: '#991B1B' }}>
                  <strong>Rejection Reason:</strong> {lastDemoResult.rejection_reason}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Section 2: Automated Batch Experiment Runner */}
      <div className="panel" style={{ marginTop: '24px' }}>
        <div className="panel-body">
          <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--deep-obsidian)', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ display: 'inline-flex', padding: '5px', borderRadius: '8px', background: 'rgba(59, 130, 246, 0.08)', color: '#2563EB' }}>
              <Play size={18} />
            </span>
            Automated Repeatable Batch Experiment Runner
          </h3>
          <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginBottom: '18px' }}>
            Execute scientific benchmark batches using identical telemetry payloads across Mode A (Baseline) and Mode B (IBE Protected).
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', alignItems: 'flex-end' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: '6px' }}>Fleet Vehicles</label>
              <select
                className="form-input"
                value={vehicleCount}
                onChange={(e) => setVehicleCount(Number(e.target.value))}
                disabled={experimentRunning}
              >
                <option value={1}>1 Vehicle (Targeted)</option>
                <option value={5}>5 Vehicles (Standard)</option>
                <option value={10}>10 Vehicles (Corridor)</option>
                <option value={25}>25 Vehicles (Metropolitan)</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: '6px' }}>Messages Per Vehicle</label>
              <select
                className="form-input"
                value={messagesPerVehicle}
                onChange={(e) => setMessagesPerVehicle(Number(e.target.value))}
                disabled={experimentRunning}
              >
                <option value={1}>1 Message</option>
                <option value={3}>3 Messages (Default)</option>
                <option value={5}>5 Messages</option>
                <option value={10}>10 Messages (Extended)</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: '6px' }}>Evaluation Mode</label>
              <select
                className="form-input"
                value={runMode}
                onChange={(e) => setRunMode(e.target.value as any)}
                disabled={experimentRunning}
              >
                <option value="both">Both (Baseline + Protected Comparison)</option>
                <option value="ibe_protected">IBE Protected Only (Mode B)</option>
                <option value="plaintext">Plaintext Baseline Only (Mode A)</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: '6px' }}>Payload Scale</label>
              <select
                className="form-input"
                value={payloadScale}
                onChange={(e) => setPayloadScale(e.target.value as any)}
                disabled={experimentRunning}
              >
                <option value="small">Small (~150B Core GPS)</option>
                <option value="medium">Medium (~450B + Diagnostics)</option>
                <option value="large">Large (~1.5KB Multi-Sensor Buffer)</option>
              </select>
            </div>

            <div>
              <button
                className="btn btn-primary"
                style={{ width: '100%', height: '38px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
                onClick={handleRunExperiment}
                disabled={experimentRunning}
              >
                <Play size={15} />
                <span>{experimentRunning ? 'Executing Batch Trial...' : 'Run Scientific Trial'}</span>
              </button>
            </div>
          </div>

          {/* Batch Result Report */}
          {lastBatchResult && (
            <div style={{ marginTop: '20px', padding: '16px 20px', borderRadius: '12px', background: 'var(--bg-surface-subtle)', border: '1px solid var(--border-strong)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <CheckCircle2 size={18} style={{ color: '#059669' }} />
                  <strong style={{ fontSize: '0.92rem', color: 'var(--deep-obsidian)' }}>
                    Batch Complete: <code>{lastBatchResult.batch_id}</code>
                  </strong>
                </div>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                  Success Rate: <strong style={{ color: '#059669' }}>{lastBatchResult.success_rate_percent}%</strong> ({lastBatchResult.total_successful}/{lastBatchResult.total_attempted})
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px' }}>
                <div style={{ padding: '14px', background: 'var(--base-white)', border: '1px solid var(--border-subtle)', borderRadius: '10px' }}>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Baseline Mode A (Plaintext)</span>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#2563EB', marginTop: '3px' }}>
                    {lastBatchResult.metrics.baseline_plaintext.median_duration_ms} ms
                  </div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '3px' }}>
                    Mean wire size: {lastBatchResult.metrics.baseline_plaintext.mean_payload_bytes} bytes
                  </div>
                </div>

                <div style={{ padding: '14px', background: 'var(--base-white)', border: '1px solid var(--border-subtle)', borderRadius: '10px' }}>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Protected Mode B (IBE-KEM + AES-256-GCM)</span>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#059669', marginTop: '3px' }}>
                    {lastBatchResult.metrics.ibe_protected.median_total_duration_ms} ms
                  </div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '3px' }}>
                    Client Enc: {lastBatchResult.metrics.ibe_protected.median_encryption_ms}ms • Server Dec: {lastBatchResult.metrics.ibe_protected.median_decryption_ms}ms
                  </div>
                </div>

                <div style={{ padding: '14px', background: 'var(--base-white)', border: '1px solid var(--border-subtle)', borderRadius: '10px' }}>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Framing & Envelope Overhead</span>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#D97706', marginTop: '3px' }}>
                    +{lastBatchResult.metrics.ibe_protected.mean_payload_expansion_percent}%
                  </div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '3px' }}>
                    Mean envelope: {lastBatchResult.metrics.ibe_protected.mean_envelope_bytes} bytes
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Section 3: Empirical Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '20px', marginTop: '24px' }}>
        <div className="panel" style={{ padding: '22px' }}>
          <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--deep-obsidian)', marginBottom: '4px' }}>
            Transmission Latency Comparison (ms)
          </h4>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
            Empirical measurements: Plaintext vs IBE encryption, decryption, and total transmission time.
          </p>
          <div style={{ height: '260px' }}>
            <Bar data={latencyChartData} options={chartOptions} />
          </div>
        </div>

        <div className="panel" style={{ padding: '22px' }}>
          <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--deep-obsidian)', marginBottom: '4px' }}>
            Payload Size & Expansion Overhead
          </h4>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
            Original telemetry payload bytes vs IBE-KEM JSON wire envelope bytes across payload categories.
          </p>
          <div style={{ height: '260px' }}>
            <Bar data={overheadChartData} options={chartOptions} />
          </div>
        </div>
      </div>

      {/* Section 4: Detailed Transmissions History Table */}
      <div className="panel" style={{ marginTop: '24px' }}>
        <div className="panel-body">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '10px' }}>
            <div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--deep-obsidian)' }}>
                Persisted Transmission Experiment Records
              </h3>
              <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                Showing {transmissions.length} of {totalRecords} logged transmissions from PostgreSQL.
              </p>
            </div>

          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              className={`btn ${activeFilter === 'all' ? 'btn-primary' : ''}`}
              style={{ fontSize: '0.78rem', padding: '4px 10px' }}
              onClick={() => { setActiveFilter('all'); setCurrentPage(1); }}
            >
              All Records
            </button>
            <button
              className={`btn ${activeFilter === 'plaintext' ? 'btn-primary' : ''}`}
              style={{ fontSize: '0.78rem', padding: '4px 10px' }}
              onClick={() => { setActiveFilter('plaintext'); setCurrentPage(1); }}
            >
              Mode A (Baseline)
            </button>
            <button
              className={`btn ${activeFilter === 'ibe_protected' ? 'btn-primary' : ''}`}
              style={{ fontSize: '0.78rem', padding: '4px 10px' }}
              onClick={() => { setActiveFilter('ibe_protected'); setCurrentPage(1); }}
            >
              Mode B (Protected)
            </button>
            <button
              className={`btn ${activeFilter === 'rejected' ? 'btn-primary' : ''}`}
              style={{ fontSize: '0.78rem', padding: '4px 10px' }}
              onClick={() => { setActiveFilter('rejected'); setCurrentPage(1); }}
            >
              Security Rejections
            </button>
          </div>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Transmission ID</th>
                <th>Vehicle</th>
                <th>Mode</th>
                <th>Category</th>
                <th>Payload Size</th>
                <th>Enc Time</th>
                <th>Dec Time</th>
                <th>Total Latency</th>
                <th>Status</th>
                <th>Inspect</th>
              </tr>
            </thead>
            <tbody>
              {transmissions.length === 0 ? (
                <tr>
                  <td colSpan={10} style={{ textAlign: 'center', padding: '30px', color: '#94a3b8' }}>
                    No transmission records found. Run an experiment above to collect data.
                  </td>
                </tr>
              ) : (
                transmissions.map((tx) => (
                  <tr key={tx.transmission_id}>
                    <td>
                      <code>{tx.transmission_id}</code>
                      {tx.batch_id && (
                        <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                          Batch: {tx.batch_id.slice(-8)}
                        </div>
                      )}
                    </td>
                    <td>
                      <strong>{tx.vehicle_identifier}</strong>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>{tx.sender_identity}</div>
                    </td>
                    <td>
                      <span
                        style={{
                          fontSize: '0.72rem',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontWeight: 600,
                          background: tx.transmission_mode === 'plaintext' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                          color: tx.transmission_mode === 'plaintext' ? '#60a5fa' : '#34d399'
                        }}
                      >
                        {tx.transmission_mode === 'plaintext' ? 'Baseline (Mode A)' : 'Protected (Mode B)'}
                      </span>
                      {tx.transmission_mode === 'ibe_protected' && (
                        <div style={{ marginTop: '3px' }}>
                          {tx.signature_verified ? (
                            <span style={{ fontSize: '0.68rem', color: '#34d399', display: 'flex', alignItems: 'center', gap: '3px' }}>
                              <ShieldCheck size={11} /> Ed25519 Verified
                            </span>
                          ) : (
                            <span style={{ fontSize: '0.68rem', color: '#f87171', display: 'flex', alignItems: 'center', gap: '3px' }}>
                              <ShieldAlert size={11} /> Auth Unverified
                            </span>
                          )}
                        </div>
                      )}
                    </td>
                    <td>
                      <span style={{ textTransform: 'capitalize', fontSize: '0.78rem' }}>{tx.payload_category}</span>
                    </td>
                    <td>
                      <span style={{ fontSize: '0.78rem' }}>{tx.original_payload_size_bytes} B</span>
                      {tx.payload_expansion_bytes > 0 && (
                        <div style={{ fontSize: '0.72rem', color: '#fbbf24' }}>
                          Env: {tx.encrypted_envelope_size_bytes} B (+{tx.payload_expansion_percent}%)
                        </div>
                      )}
                    </td>
                    <td style={{ fontSize: '0.8rem' }}>{tx.encryption_duration_ms > 0 ? `${tx.encryption_duration_ms}ms` : '—'}</td>
                    <td style={{ fontSize: '0.8rem' }}>{tx.decryption_duration_ms > 0 ? `${tx.decryption_duration_ms}ms` : '—'}</td>
                    <td style={{ fontSize: '0.8rem', fontWeight: 600 }}>{tx.total_duration_ms} ms</td>
                    <td>
                      <span
                        style={{
                          fontSize: '0.72rem',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontWeight: 600,
                          background: tx.status === 'success' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                          color: tx.status === 'success' ? '#34d399' : '#f87171'
                        }}
                      >
                        {tx.status.toUpperCase()}
                      </span>
                      {tx.rejection_reason && (
                        <div style={{ fontSize: '0.68rem', color: '#fca5a5', maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={tx.rejection_reason}>
                          {tx.rejection_reason}
                        </div>
                      )}
                    </td>
                    <td>
                      <button
                        className="btn"
                        style={{ fontSize: '0.74rem', padding: '2px 8px' }}
                        onClick={() => setSelectedTx(tx)}
                      >
                        Details
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalRecords > 15 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px' }}>
            <span style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
              Page {currentPage} of {Math.ceil(totalRecords / 15)}
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                className="btn"
                style={{ fontSize: '0.8rem', padding: '4px 10px' }}
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </button>
              <button
                className="btn"
                style={{ fontSize: '0.8rem', padding: '4px 10px' }}
                disabled={currentPage >= Math.ceil(totalRecords / 15)}
                onClick={() => setCurrentPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          </div>
        )}
        </div>
      </div>

      {/* Record Inspection Modal */}
      {selectedTx && (
        <div className="modal-backdrop" onClick={() => setSelectedTx(null)}>
          <div className="modal-content" style={{ maxWidth: '650px', background: 'var(--base-white)', border: '1px solid var(--border-strong)', borderRadius: '16px', padding: '24px', boxShadow: '0 12px 40px rgba(0,0,0,0.12)' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--deep-obsidian)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ display: 'inline-flex', padding: '5px', borderRadius: '8px', background: 'rgba(59, 130, 246, 0.08)', color: '#2563EB' }}>
                  <FileText size={18} />
                </span>
                Transmission Record Inspector
              </h3>
              <button className="btn-close" onClick={() => setSelectedTx(null)} style={{ border: 'none', background: 'transparent', fontSize: '1.2rem', cursor: 'pointer', color: 'var(--text-muted)' }}>✕</button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', fontSize: '0.84rem', marginBottom: '18px' }}>
              <div style={{ padding: '10px 12px', background: 'var(--bg-surface-subtle)', borderRadius: '8px' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.76rem', display: 'block' }}>Transmission ID</span>
                <div style={{ marginTop: '2px' }}><code style={{ color: 'var(--deep-obsidian)', fontWeight: 600 }}>{selectedTx.transmission_id}</code></div>
              </div>
              <div style={{ padding: '10px 12px', background: 'var(--bg-surface-subtle)', borderRadius: '8px' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.76rem', display: 'block' }}>Vehicle Identifier</span>
                <div style={{ marginTop: '2px', color: 'var(--deep-obsidian)', fontWeight: 700 }}>{selectedTx.vehicle_identifier}</div>
              </div>
              <div style={{ padding: '10px 12px', background: 'var(--bg-surface-subtle)', borderRadius: '8px' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.76rem', display: 'block' }}>Sender Identity</span>
                <div style={{ marginTop: '2px' }}><code style={{ color: 'var(--deep-obsidian)' }}>{selectedTx.sender_identity}</code></div>
              </div>
              <div style={{ padding: '10px 12px', background: 'var(--bg-surface-subtle)', borderRadius: '8px' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.76rem', display: 'block' }}>Recipient Server</span>
                <div style={{ marginTop: '2px' }}><code style={{ color: 'var(--deep-obsidian)' }}>{selectedTx.recipient_identity}</code></div>
              </div>
              <div style={{ padding: '10px 12px', background: 'var(--bg-surface-subtle)', borderRadius: '8px' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.76rem', display: 'block' }}>Transmission Mode</span>
                <div style={{ marginTop: '2px', color: 'var(--deep-obsidian)', fontWeight: 600 }}>{selectedTx.transmission_mode.toUpperCase()}</div>
              </div>
              <div style={{ padding: '10px 12px', background: 'var(--bg-surface-subtle)', borderRadius: '8px' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.76rem', display: 'block' }}>Status</span>
                <span style={{ color: selectedTx.status === 'success' ? '#059669' : '#DC2626', fontWeight: 700, marginTop: '2px', display: 'inline-block' }}>
                  {selectedTx.status.toUpperCase()}
                </span>
              </div>
              <div style={{ padding: '10px 12px', background: 'var(--bg-surface-subtle)', borderRadius: '8px' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.76rem', display: 'block' }}>Wire Size</span>
                <div style={{ marginTop: '2px', color: 'var(--deep-obsidian)' }}>{selectedTx.encrypted_envelope_size_bytes} bytes (+{selectedTx.payload_expansion_bytes}B overhead)</div>
              </div>
              <div style={{ padding: '10px 12px', background: 'var(--bg-surface-subtle)', borderRadius: '8px' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.76rem', display: 'block' }}>Round-trip Latency</span>
                <div style={{ marginTop: '2px', color: 'var(--deep-obsidian)', fontWeight: 700 }}>{selectedTx.total_duration_ms} ms (Enc: {selectedTx.encryption_duration_ms}ms, Dec: {selectedTx.decryption_duration_ms}ms)</div>
              </div>
            </div>

            {selectedTx.rejection_reason && (
              <div style={{ padding: '12px 14px', background: 'rgba(220, 38, 38, 0.05)', border: '1px solid rgba(220, 38, 38, 0.25)', borderRadius: '8px', marginBottom: '18px', fontSize: '0.82rem', color: '#991B1B' }}>
                <strong>Rejection Reason:</strong> {selectedTx.rejection_reason}
              </div>
            )}

            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '8px' }}>Security Checks Passed / Flags:</div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '20px' }}>
              <span style={{ fontSize: '0.72rem', padding: '3px 10px', borderRadius: '9999px', fontWeight: 600, background: selectedTx.tampered_flag ? 'rgba(220, 38, 38, 0.08)' : 'rgba(5, 150, 105, 0.08)', color: selectedTx.tampered_flag ? '#DC2626' : '#059669', border: `1px solid ${selectedTx.tampered_flag ? 'rgba(220, 38, 38, 0.2)' : 'rgba(5, 150, 105, 0.2)'}` }}>
                {selectedTx.tampered_flag ? 'Tampering Detected' : 'Ciphertext Integrity Valid'}
              </span>
              <span style={{ fontSize: '0.72rem', padding: '3px 10px', borderRadius: '9999px', fontWeight: 600, background: selectedTx.replayed_flag ? 'rgba(220, 38, 38, 0.08)' : 'rgba(5, 150, 105, 0.08)', color: selectedTx.replayed_flag ? '#DC2626' : '#059669', border: `1px solid ${selectedTx.replayed_flag ? 'rgba(220, 38, 38, 0.2)' : 'rgba(5, 150, 105, 0.2)'}` }}>
                {selectedTx.replayed_flag ? 'Replay Detected' : 'Message Freshness Valid'}
              </span>
              <span style={{ fontSize: '0.72rem', padding: '3px 10px', borderRadius: '9999px', fontWeight: 600, background: selectedTx.unauthorized_identity_flag ? 'rgba(220, 38, 38, 0.08)' : 'rgba(5, 150, 105, 0.08)', color: selectedTx.unauthorized_identity_flag ? '#DC2626' : '#059669', border: `1px solid ${selectedTx.unauthorized_identity_flag ? 'rgba(220, 38, 38, 0.2)' : 'rgba(5, 150, 105, 0.2)'}` }}>
                {selectedTx.unauthorized_identity_flag ? 'Unauthorized Identity' : 'Identity Enrolled & Bound'}
              </span>
              <span style={{ fontSize: '0.72rem', padding: '3px 10px', borderRadius: '9999px', fontWeight: 600, background: selectedTx.signature_verified ? 'rgba(5, 150, 105, 0.08)' : 'rgba(220, 38, 38, 0.08)', color: selectedTx.signature_verified ? '#059669' : '#DC2626', border: `1px solid ${selectedTx.signature_verified ? 'rgba(5, 150, 105, 0.2)' : 'rgba(220, 38, 38, 0.2)'}` }}>
                {selectedTx.signature_verified ? 'Ed25519 Signature Verified' : 'Ed25519 Signature Unverified'}
              </span>
            </div>

            <button className="btn btn-secondary" style={{ width: '100%' }} onClick={() => setSelectedTx(null)}>
              Close Inspector
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
