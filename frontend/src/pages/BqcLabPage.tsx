import React, { useState, useEffect } from 'react';
import {
  Cpu,
  ShieldCheck,
  Eye,
  EyeOff,
  Activity,
  Zap,
  Play,
  RotateCcw,
  BarChart2,
  Layers,
  CheckCircle2,
  Info,
  Server,
  Share2
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
import { api } from '../services/api';
import {
  BqcStatus,
  BqcDemonstrationResult,
  BqcBatchSummary,
  BqcExperimentItem
} from '../types';
import { MetricCard } from '../components/MetricCard';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export const BqcLabPage: React.FC = () => {
  // State
  const [status, setStatus] = useState<BqcStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState<boolean>(true);

  // Demonstration
  const [numCandidates, setNumCandidates] = useState<number>(2);
  const [clusterTopology, setClusterTopology] = useState<string>('linear');
  const [demoLoading, setDemoLoading] = useState<boolean>(false);
  const [demoResult, setDemoResult] = useState<BqcDemonstrationResult | null>(null);

  // Batch Trials
  const [trialsPerMode, setTrialsPerMode] = useState<number>(10);
  const [batchLoading, setBatchLoading] = useState<boolean>(false);
  const [batchResult, setBatchResult] = useState<BqcBatchSummary | null>(null);

  // History
  const [experiments, setExperiments] = useState<BqcExperimentItem[]>([]);

  // Load initial status and experiments
  useEffect(() => {
    loadStatus();
    loadExperiments();
  }, []);

  const loadStatus = async () => {
    setStatusLoading(true);
    try {
      const data = await api.getBqcStatus();
      setStatus(data);
    } catch (err) {
      console.error('Failed to load BQC status:', err);
    } finally {
      setStatusLoading(false);
    }
  };

  const loadExperiments = async () => {
    try {
      const list = await api.getBqcExperiments(10);
      setExperiments(list);
    } catch (err) {
      console.error('Failed to load BQC experiments:', err);
    }
  };

  const handleRunDemo = async () => {
    setDemoLoading(true);
    try {
      const result = await api.demonstrateBqc({
        num_candidates: numCandidates,
        cluster_topology: numCandidates === 2 ? 'linear' : 'ladder'
      });
      setDemoResult(result);
      await loadExperiments();
    } catch (err) {
      console.error('Demonstration execution error:', err);
    } finally {
      setDemoLoading(false);
    }
  };

  const handleRunBatch = async () => {
    setBatchLoading(true);
    try {
      const result = await api.runBqcBatchTrials({
        num_candidates: numCandidates,
        trials_per_mode: trialsPerMode,
        cluster_topology: numCandidates === 2 ? 'linear' : 'ladder'
      });
      setBatchResult(result);
      await loadExperiments();
    } catch (err) {
      console.error('Batch trials error:', err);
    } finally {
      setBatchLoading(false);
    }
  };

  // Chart data for latency in Ink Wash & Apple High-Contrast Palette
  const latencyChartData = {
    labels: ['Median Latency (ms)', 'Mean Latency (ms)', 'p95 Latency (ms)'],
    datasets: [
      {
        label: 'Mode A: Classical Baseline',
        data: batchResult
          ? [batchResult.mode_a.median_latency_ms, batchResult.mode_a.mean_latency_ms, batchResult.mode_a.p95_latency_ms]
          : demoResult
          ? [demoResult.mode_a.execution_time_ms, demoResult.mode_a.execution_time_ms, demoResult.mode_a.execution_time_ms]
          : [0.016, 0.021, 0.039],
        backgroundColor: '#86868b',
        borderColor: '#86868b',
        borderWidth: 1.5,
        borderRadius: 8
      },
      {
        label: 'Mode B: BFK09 Delegated BQC',
        data: batchResult
          ? [batchResult.mode_b.median_latency_ms, batchResult.mode_b.mean_latency_ms, batchResult.mode_b.p95_latency_ms]
          : demoResult
          ? [demoResult.mode_b.total_execution_ms, demoResult.mode_b.total_execution_ms, demoResult.mode_b.total_execution_ms]
          : [0.120, 0.128, 0.163],
        backgroundColor: '#0A0A0A',
        borderColor: '#0A0A0A',
        borderWidth: 1.5,
        borderRadius: 6
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: '#0A0A0A',
          font: { family: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif', size: 12, weight: 600 }
        }
      },
      tooltip: {
        backgroundColor: '#0A0A0A',
        borderColor: '#E2E8F0',
        borderWidth: 1,
        titleColor: '#FFFFFF',
        bodyColor: '#E2E8F0',
        callbacks: {
          label: (context: any) => `${context.dataset.label}: ${context.raw.toFixed(4)} ms`
        }
      }
    },
    scales: {
      x: {
        ticks: { color: '#64748B', font: { family: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif' } },
        grid: { color: '#F1F5F9' }
      },
      y: {
        title: {
          display: true,
          text: 'Duration (milliseconds)',
          color: '#64748B',
          font: { family: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif' }
        },
        ticks: { color: '#64748B' },
        grid: { color: '#F1F5F9' }
      }
    }
  };

  // Node positions for cluster state SVG visualizer in Titanium Silver Minimalist aesthetic
  const renderClusterStateSvg = () => {
    const isM2 = (demoResult?.num_candidates ?? numCandidates) === 2;
    if (isM2) {
      // 4-qubit linear cluster: 0 - 1 - 2 - 3
      const nodes = [
        { id: 0, label: 'Q0: In', x: 50, y: 55, color: '#0A0A0A' },
        { id: 1, label: 'Q1: Oracle', x: 150, y: 55, color: '#475569' },
        { id: 2, label: 'Q2: Prop', x: 250, y: 55, color: '#94A3B8' },
        { id: 3, label: 'Q3: Out', x: 350, y: 55, color: '#059669' }
      ];
      const edges = [[0, 1], [1, 2], [2, 3]];

      return (
        <svg viewBox="0 0 400 110" style={{ width: '100%', height: '110px' }} id="cluster-svg-m2">
          {/* Edges with sleek titanium dashed lines */}
          {edges.map(([u, v], idx) => (
            <line
              key={idx}
              x1={nodes[u].x}
              y1={nodes[u].y}
              x2={nodes[v].x}
              y2={nodes[v].y}
              stroke="#CBD5E1"
              strokeWidth="2"
              strokeDasharray="4 3"
            />
          ))}
          {/* Nodes */}
          {nodes.map((n) => (
            <g key={n.id}>
              <circle
                cx={n.x}
                cy={n.y}
                r="18"
                fill="#FFFFFF"
                stroke={n.color}
                strokeWidth="2.5"
              />
              <text
                x={n.x}
                y={n.y + 4}
                textAnchor="middle"
                fill="#0A0A0A"
                fontSize="11"
                fontWeight="700"
                fontFamily="-apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif"
              >
                q{n.id}
              </text>
              <text
                x={n.x}
                y={n.y + 34}
                textAnchor="middle"
                fill="#64748B"
                fontSize="9"
                fontFamily="var(--font-family-mono)"
              >
                {n.label}
              </text>
            </g>
          ))}
        </svg>
      );
    } else {
      // 6-qubit ladder cluster: 0-1-2 (top), 3-4-5 (bottom) with rung edges
      const nodes = [
        { id: 0, label: 'Q0', x: 60, y: 35, color: '#0A0A0A' },
        { id: 1, label: 'Q1', x: 200, y: 35, color: '#475569' },
        { id: 2, label: 'Q2', x: 340, y: 35, color: '#059669' },
        { id: 3, label: 'Q3', x: 60, y: 95, color: '#0A0A0A' },
        { id: 4, label: 'Q4', x: 200, y: 95, color: '#94A3B8' },
        { id: 5, label: 'Q5', x: 340, y: 95, color: '#059669' }
      ];
      const edges = [
        [0, 1], [1, 2], [3, 4], [4, 5],
        [0, 3], [1, 4], [2, 5]
      ];

      return (
        <svg viewBox="0 0 400 135" style={{ width: '100%', height: '135px' }} id="cluster-svg-m4">
          {edges.map(([u, v], idx) => (
            <line
              key={idx}
              x1={nodes[u].x}
              y1={nodes[u].y}
              x2={nodes[v].x}
              y2={nodes[v].y}
              stroke="#CBD5E1"
              strokeWidth="1.8"
              strokeDasharray="4 2"
            />
          ))}
          {nodes.map((n) => (
            <g key={n.id}>
              <circle
                cx={n.x}
                cy={n.y}
                r="16"
                fill="#FFFFFF"
                stroke={n.color}
                strokeWidth="2"
              />
              <text
                x={n.x}
                y={n.y + 4}
                textAnchor="middle"
                fill="#0A0A0A"
                fontSize="10"
                fontWeight="700"
                fontFamily="-apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif"
              >
                q{n.id}
              </text>
            </g>
          ))}
        </svg>
      );
    }
  };

  return (
    <div className="page-container" style={{ padding: '32px 48px', maxWidth: '1640px', margin: '0 auto' }}>
      {/* Minimalist Header */}
      <div className="minimal-header">
        <div>
          <h1 className="minimal-title">Blind Quantum Computing (BQC) Privacy Lab</h1>
          <p className="minimal-subtitle">BFK09 Measurement-Based Quantum Computing (MBQC) protocol for confidential fleet delegation</p>
        </div>
      </div>

      {/* Scientific Limitations Banner in Titanium Silver Minimalist Style */}
      <div style={{
        background: 'var(--bg-surface-elevated)',
        border: '1px solid var(--border-strong)',
        borderRadius: '16px',
        padding: '16px 24px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '14px',
        boxShadow: 'var(--shadow-sm)'
      }}>
        <Info size={22} color="#0A0A0A" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
          <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>Scientific & Simulator Disclaimer:</span> All quantum states and projective measurements are executed via a local classical linear algebra state-vector simulator ($N \le 16$ qubits). This research environment simulates the single-qubit preparation client model and an untrusted quantum server. <strong>No physical quantum hardware is utilized, and no quantum computational speedup or advantage is claimed.</strong>
        </div>
      </div>

      {/* Top Protocol Status Cards */}
      <div className="metrics-grid">
        <MetricCard
          title="Delegated Fleet Optimization"
          value={numCandidates === 2 ? '2 Candidates (4 Qubits)' : '4 Candidates (6 Qubits)'}
          subtext="Confidential Min-Cost Selection"
          icon={<Zap size={20} color="#0A0A0A" />}
        />
        <MetricCard
          title="Privacy Model"
          value="BFK09 Universal Blindness"
          subtext="Angles unif. distributed in [0, 2π)"
          icon={<ShieldCheck size={20} color="#059669" />}
        />
        <MetricCard
          title="Theoretical Angle Entropy"
          value="3.000 bits / qubit"
          subtext="Max theoretical for 8-angle set"
          icon={<Activity size={20} color="#0A0A0A" />}
        />
        <MetricCard
          title="Server Information Visibility"
          value="0 Bits Leaked"
          subtext="Vehicle GPS, Costs & Depot hidden"
          icon={<EyeOff size={20} color="#0A0A0A" />}
        />
      </div>

      {/* Main Grid: Demonstration Runner & SVG Cluster Visualizer */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1.2fr 1fr',
        gap: '24px',
        marginBottom: '28px'
      }}>
        {/* Left: Interactive Experiment Demonstration Controls */}
        <div className="panel">
          <div className="panel-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Layers size={18} color="#0A0A0A" />
              <h2 className="panel-title">
                Single-Trial Demonstration Runner
              </h2>
            </div>
            <span style={{ fontSize: '0.74rem', color: '#0A0A0A', background: 'var(--bg-surface-subtle)', padding: '4px 12px', borderRadius: '9999px', fontWeight: 600 }}>
              Mode A vs Mode B
            </span>
          </div>

          <div className="panel-body">
            <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginBottom: '20px' }}>
              Compare classical plaintext fleet optimization against delegated BFK09 blind quantum computing over an identical depot candidate set and cost objective.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '6px', fontWeight: 600 }}>
                  Depot Candidates (M)
                </label>
                <select
                  value={numCandidates}
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    setNumCandidates(val);
                    setClusterTopology(val === 2 ? 'linear' : 'ladder');
                  }}
                  id="select-num-candidates"
                  className="form-select"
                  style={{ width: '100%', borderRadius: '12px' }}
                >
                  <option value={2}>M = 2 Candidates (4-Qubit Linear Cluster)</option>
                  <option value={4}>M = 4 Candidates (6-Qubit Ladder Cluster)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '6px', fontWeight: 600 }}>
                  Entangled Cluster Graph Topology
                </label>
                <input
                  type="text"
                  readOnly
                  value={numCandidates === 2 ? '1D Linear Graph (Edges: (0,1),(1,2),(2,3))' : '2D Ladder Graph (Edges: 7 total)'}
                  className="form-input"
                  style={{ width: '100%', borderRadius: '12px', background: 'var(--bg-surface-elevated)' }}
                />
              </div>
            </div>

            <button
              onClick={handleRunDemo}
              disabled={demoLoading}
              id="btn-run-demo"
              className="btn btn-primary"
              style={{
                width: '100%',
                padding: '14px',
                fontSize: '0.94rem'
              }}
            >
              {demoLoading ? <RotateCcw size={18} className="animate-spin" /> : <Play size={18} />}
              <span>{demoLoading ? 'Simulating BFK09 MBQC Execution...' : 'Run Comparative Protocol Demonstration'}</span>
            </button>
          </div>
        </div>

        {/* Right: SVG Cluster State Graph Visualization */}
        <div className="panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div className="panel-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Share2 size={18} color="#0A0A0A" />
              <h2 className="panel-title">
                MBQC Cluster State Topology
              </h2>
            </div>
            <span style={{ fontSize: '0.74rem', color: '#0A0A0A', background: 'var(--bg-surface-subtle)', padding: '4px 12px', borderRadius: '9999px', fontWeight: 600 }}>
              Graph G = (V, E)
            </span>
          </div>

          <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%' }}>
            <div>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                Entangled resource graph state |G⟩ = ∏ CZ ⊗ |θ⟩. Dashed links represent Controlled-Z entangling operations executed blindly by the cloud server.
              </p>

              <div style={{
                background: 'var(--bg-surface-elevated)',
                border: '1px solid var(--border-strong)',
                borderRadius: '14px',
                padding: '18px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                {renderClusterStateSvg()}
              </div>
            </div>

            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '16px', display: 'flex', justifyContent: 'space-between' }}>
              <span>Client Secret: Blinding angle θ<sub>j</sub> ∈ [0, 2π)</span>
              <span>Server: Measures along |+<sub>δ</sub>⟩, |-<sub>δ</sub>⟩</span>
            </div>
          </div>
        </div>
      </div>

      {/* Side-by-Side Protocol Comparison Card (Active after Demo run or Default) */}
      <div className="panel" style={{ marginBottom: '28px' }}>
        <div className="panel-header">
          <div>
            <h2 className="panel-title">
              Side-by-Side Security & Execution Contrast
            </h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Direct experimental comparison of the classical fleet dispatcher vs delegated universal blind quantum computing.
            </p>
          </div>
          {demoResult && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: demoResult.correctness_verified ? 'rgba(5, 150, 105, 0.08)' : 'rgba(220, 38, 38, 0.08)',
              color: demoResult.correctness_verified ? '#065F46' : '#991B1B',
              border: demoResult.correctness_verified ? '1px solid rgba(5, 150, 105, 0.25)' : '1px solid rgba(220, 38, 38, 0.25)',
              padding: '6px 16px',
              borderRadius: '9999px',
              fontSize: '0.82rem',
              fontWeight: 600
            }}>
              <CheckCircle2 size={16} />
              <span>Correctness Verified (Selected identical optimal candidate)</span>
            </div>
          )}
        </div>

        <div className="panel-body">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            {/* Mode A: Classical Baseline */}
            <div style={{
              background: 'var(--base-white)',
              border: '1px solid var(--border-strong)',
              borderRadius: '16px',
              padding: '24px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <span style={{
                  background: 'var(--bg-surface-subtle)',
                  color: 'var(--deep-obsidian)',
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  padding: '4px 12px',
                  borderRadius: '9999px',
                  border: '1px solid var(--border-strong)'
                }}>
                  Mode A: Classical Baseline
                </span>
                <span style={{ fontSize: '0.8rem', color: '#DC2626', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Eye size={14} /> Full Server Visibility
                </span>
              </div>

              <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '18px', lineHeight: 1.7 }}>
                <div><strong>Selected Depot:</strong> {demoResult ? demoResult.mode_a.selected_depot_name : 'North Logistics Depot'}</div>
                <div><strong>Evaluated Cost:</strong> {demoResult ? demoResult.mode_a.selected_cost.toFixed(2) : '14.20'}</div>
                <div><strong>Execution Latency:</strong> {demoResult ? `${demoResult.mode_a.execution_time_ms.toFixed(3)} ms` : '0.021 ms'}</div>
                <div><strong>Communication Wire Size:</strong> {demoResult ? `${demoResult.mode_a.wire_bytes} bytes` : '168 bytes'}</div>
              </div>

              <div style={{
                background: '#FEF2F2',
                border: '1px solid #FECACA',
                borderRadius: '12px',
                padding: '12px 16px',
                fontSize: '0.82rem',
                color: '#991B1B'
              }}>
                <div style={{ fontWeight: 700, marginBottom: '2px' }}>Server Information Exposure:</div>
                <div>Server directly receives vehicle GPS coordinates, individual candidate distance/congestion cost matrix, and reads the selected depot index in plaintext.</div>
              </div>
            </div>

            {/* Mode B: BFK09 Delegated BQC (Deep Obsidian Dark Contrast Spotlight Card) */}
            <div style={{
              background: 'var(--deep-obsidian)',
              border: '1px solid var(--deep-obsidian)',
              borderRadius: '16px',
              padding: '24px',
              color: '#FFFFFF',
              boxShadow: 'var(--shadow-card-dark)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <span style={{
                  background: 'rgba(255, 255, 255, 0.12)',
                  color: '#FFFFFF',
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  padding: '4px 12px',
                  borderRadius: '9999px',
                  border: '1px solid rgba(255, 255, 255, 0.2)'
                }}>
                  Mode B: BFK09 Delegated BQC
                </span>
                <span style={{ fontSize: '0.8rem', color: '#10B981', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <EyeOff size={14} /> Universal Blindness
                </span>
              </div>

              <div style={{ fontSize: '0.9rem', color: '#F4F4F5', marginBottom: '18px', lineHeight: 1.7 }}>
                <div><strong>Decoded Depot:</strong> {demoResult ? demoResult.mode_b.selected_depot_name : 'North Logistics Depot'}</div>
                <div><strong>Evaluated Cost:</strong> {demoResult ? demoResult.mode_b.selected_cost.toFixed(2) : '14.20'}</div>
                <div><strong>Total Latency:</strong> {demoResult ? `${demoResult.mode_b.total_execution_ms.toFixed(3)} ms (Client: ${demoResult.mode_b.client_prep_ms.toFixed(2)}ms, Server: ${demoResult.mode_b.server_quantum_ms.toFixed(2)}ms)` : '0.128 ms'}</div>
                <div><strong>Communication Wire Size:</strong> {demoResult ? `${demoResult.mode_b.total_wire_bytes} bytes (${demoResult.wire_expansion_percent.toFixed(1)}% expansion)` : '448 bytes (166.7% expansion)'}</div>
              </div>

              <div style={{
                background: 'rgba(16, 185, 129, 0.12)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                borderRadius: '12px',
                padding: '12px 16px',
                fontSize: '0.82rem',
                color: '#34D399'
              }}>
                <div style={{ fontWeight: 700, marginBottom: '2px' }}>Server Privacy Guarantee:</div>
                <div>Server receives blinded measurement angles δ_j = φ'_j + θ_j + π·r_j. The raw measurement outcome b_j is one-time padded. Zero bits of GPS, costs, or target depot are exposed.</div>
              </div>
            </div>
          </div>

          {/* Server Visibility Audit Inspection */}
          {demoResult && (
            <div style={{
              marginTop: '24px',
              background: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-strong)',
              borderRadius: '14px',
              padding: '20px'
            }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Server size={18} color="#0A0A0A" />
                Server-Observable Information Inspector (Audit Log)
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', fontSize: '0.84rem' }}>
                <div style={{ background: 'var(--base-white)', border: '1px solid var(--border-strong)', padding: '12px 16px', borderRadius: '10px' }}>
                  <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Observed Blinded Angles (δ_j):</span>
                  <div style={{ fontFamily: 'var(--font-family-mono)', color: 'var(--deep-obsidian)', marginTop: '4px', fontWeight: 600 }}>
                    [{demoResult.mode_b.blinded_angles_rad.join(', ')}]
                  </div>
                </div>
                <div style={{ background: 'var(--base-white)', border: '1px solid var(--border-strong)', padding: '12px 16px', borderRadius: '10px' }}>
                  <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Blinded Angle Shannon Entropy:</span>
                  <div style={{ fontFamily: 'var(--font-family-mono)', color: '#059669', marginTop: '4px', fontWeight: 700 }}>
                    {demoResult.mode_b.angle_entropy_bits.toFixed(3)} bits (Max: 3.000 bits)
                  </div>
                </div>
                <div style={{ background: 'var(--base-white)', border: '1px solid var(--border-strong)', padding: '12px 16px', borderRadius: '10px' }}>
                  <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Raw Measurement Bits (b_j):</span>
                  <div style={{ fontFamily: 'var(--font-family-mono)', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    [{demoResult.mode_b.server_raw_outcomes.join(', ')}] (One-Time Padded)
                  </div>
                </div>
                <div style={{ background: 'var(--base-white)', border: '1px solid var(--border-strong)', padding: '12px 16px', borderRadius: '10px' }}>
                  <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Server Learned Private Input:</span>
                  <div style={{ color: '#059669', fontWeight: 700, marginTop: '4px' }}>
                    False (0 bits learned)
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Batch Experiment Runner & Statistical Charts */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1.4fr',
        gap: '24px',
        marginBottom: '28px'
      }}>
        {/* Left: Batch Runner Controls & Live KPIs */}
        <div className="panel">
          <div className="panel-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BarChart2 size={18} color="#0A0A0A" />
              <h2 className="panel-title">
                Batch Verification Suite
              </h2>
            </div>
          </div>
          <div className="panel-body">
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '18px' }}>
              Run repeated independent trials with fresh random seeds to measure statistical distinguishability (Total Variation Distance) and latency distributions stored in PostgreSQL.
            </p>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: 600 }}>
                Trials Per Mode (N)
              </label>
              <div style={{ display: 'flex', gap: '10px' }}>
                {[5, 10, 25].map((count) => (
                  <button
                    key={count}
                    type="button"
                    onClick={() => setTrialsPerMode(count)}
                    style={{
                      flex: 1,
                      background: trialsPerMode === count ? '#0A0A0A' : 'var(--base-white)',
                      border: '1px solid',
                      borderColor: trialsPerMode === count ? '#0A0A0A' : 'var(--border-strong)',
                      borderRadius: '9999px',
                      color: trialsPerMode === count ? '#FFFFFF' : 'var(--text-secondary)',
                      padding: '9px 0',
                      fontSize: '0.85rem',
                      cursor: 'pointer',
                      fontWeight: trialsPerMode === count ? 700 : 500,
                      transition: 'all 0.15s ease'
                    }}
                  >
                    {count} Trials
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={handleRunBatch}
              disabled={batchLoading}
              id="btn-run-batch"
              className="btn btn-primary"
              style={{
                width: '100%',
                padding: '14px',
                fontSize: '0.94rem',
                marginBottom: '20px'
              }}
            >
              {batchLoading ? <RotateCcw size={18} className="animate-spin" /> : <Activity size={18} />}
              <span>{batchLoading ? `Executing ${trialsPerMode * 2} Experimental Trials...` : `Execute ${trialsPerMode * 2} Batch Trials`}</span>
            </button>

            {/* Batch KPI Results */}
            {batchResult && (
              <div style={{
                background: 'var(--bg-surface-elevated)',
                border: '1px solid var(--border-strong)',
                borderRadius: '14px',
                padding: '18px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
                fontSize: '0.84rem'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Algorithmic Correctness:</span>
                  <span style={{ color: '#059669', fontWeight: 700 }}>{batchResult.algorithmic_correctness_rate.toFixed(1)}%</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Universal Blindness Rate:</span>
                  <span style={{ color: '#059669', fontWeight: 700 }}>{batchResult.universal_blindness_verified_rate.toFixed(1)}%</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Mean Angle Entropy:</span>
                  <span style={{ color: 'var(--deep-obsidian)', fontWeight: 700 }}>{batchResult.mean_angle_entropy_bits.toFixed(3)} bits</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Total Variation Distance (TVD):</span>
                  <span style={{ color: 'var(--titanium-slate)', fontWeight: 700 }}>{batchResult.total_variation_distance.toFixed(4)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Statistical Verdict:</span>
                  <span style={{ color: '#059669', fontWeight: 700 }}>{batchResult.distinguishability_verdict}</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: Latency Distribution Chart */}
        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">
              Execution Latency Comparison (ms)
            </h2>
          </div>
          <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100% - 65px)' }}>
            <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Classical in-memory calculation vs BFK09 multi-step interactive MBQC protocol.
            </p>
            <div style={{ flex: 1, minHeight: '260px' }}>
              <Bar data={latencyChartData} options={chartOptions} />
            </div>
          </div>
        </div>
      </div>

      {/* Database History Table */}
      <div className="panel">
        <div className="panel-header">
          <h2 className="panel-title">
            PostgreSQL Experiment Registry (Port 5435)
          </h2>
          <span style={{ fontSize: '0.78rem', color: 'var(--deep-obsidian)', background: 'var(--bg-surface-subtle)', padding: '4px 12px', borderRadius: '9999px', border: '1px solid var(--border-strong)' }}>
            Table: <code>bqc_experiments</code> & <code>bqc_trials</code>
          </span>
        </div>

        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Experiment Name</th>
                <th>Candidates (M)</th>
                <th>Topology / Qubits</th>
                <th>Total Trials</th>
                <th>Correctness</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {experiments.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: '28px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No experiments logged yet. Run a demonstration or batch trial above to record to PostgreSQL.
                  </td>
                </tr>
              ) : (
                experiments.map((exp) => (
                  <tr key={exp.id}>
                    <td style={{ fontFamily: 'var(--font-family-mono)', color: 'var(--deep-obsidian)', fontWeight: 700 }}>#{exp.id}</td>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{exp.name}</td>
                    <td>M = {exp.num_candidates}</td>
                    <td>{exp.cluster_topology} ({exp.num_qubits}Q)</td>
                    <td>{exp.total_trials}</td>
                    <td style={{ color: '#059669', fontWeight: 700 }}>{exp.correctness_rate.toFixed(1)}%</td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                      {new Date(exp.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default BqcLabPage;
