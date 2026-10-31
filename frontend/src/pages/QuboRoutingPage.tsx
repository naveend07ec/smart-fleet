import React, { useState, useEffect } from 'react';
import {
  Compass,
  Play,
  RotateCcw,
  Zap,
  TrendingDown,
  Activity,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Download,
  Trash2,
  Clock,
  Sparkles,
  Info,
  Sliders,
  BarChart3,
  Check,
  XCircle,
  HelpCircle,
  GitCompare,
  Eye,
  Cpu
} from 'lucide-react';
import { api } from '../services/api';
import {
  OptimizationRunResponse,
  OptimizationExperimentListItem,
  OptimizationScenarioInfo,
  MethodComparisonSummary,
  VehicleRouteResult
} from '../types';

export const QuboRoutingPage: React.FC = () => {
  // Scenario & Solver Parameters
  const [selectedScenario, setSelectedScenario] = useState<string>('small');
  const [scenarios, setScenarios] = useState<OptimizationScenarioInfo[]>([]);
  const [trialCount, setTrialCount] = useState<number>(3);
  const [randomSeed, setRandomSeed] = useState<number>(42);
  const [saIterations, setSaIterations] = useState<number>(1000);
  const [initialTemp, setInitialTemp] = useState<number>(100.0);
  const [coolingRate, setCoolingRate] = useState<number>(0.985);
  const [penaltyVisit, setPenaltyVisit] = useState<number>(150.0);
  const [penaltySlot, setPenaltySlot] = useState<number>(120.0);
  const [penaltyContig, setPenaltyContig] = useState<number>(80.0);
  const [penaltyCap, setPenaltyCap] = useState<number>(100.0);
  const [includeBruteForce, setIncludeBruteForce] = useState<boolean>(true);
  const [selectedMethod, setSelectedMethod] = useState<string>('all_comparative');

  // UI State
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeMethodTab, setActiveMethodTab] = useState<'qubo_sa' | 'classical_sa' | 'greedy' | 'brute_force_exact'>('qubo_sa');
  const [optimizationResult, setOptimizationResult] = useState<OptimizationRunResponse | null>(null);
  const [experiments, setExperiments] = useState<OptimizationExperimentListItem[]>([]);
  const [loadingExperiments, setLoadingExperiments] = useState<boolean>(false);
  const [selectedExpDetail, setSelectedExpDetail] = useState<any | null>(null);
  const [selectedForCompare, setSelectedForCompare] = useState<number[]>([]);
  const [comparisonResults, setComparisonResults] = useState<any[] | null>(null);

  // Palette for vehicle routes
  const routeColors = ['#2563EB', '#7C3AED', '#059669', '#D97706', '#DB2777'];

  // Load scenarios and experiments on mount
  useEffect(() => {
    loadScenarios();
    loadExperiments();
  }, []);

  const loadScenarios = async () => {
    try {
      const scList = await api.getOptimizationScenarios();
      setScenarios(scList);
    } catch {
      // Fallback
    }
  };

  const loadExperiments = async () => {
    setLoadingExperiments(true);
    try {
      const list = await api.getOptimizationExperiments(30);
      setExperiments(list);
    } catch {
      // ignore
    } finally {
      setLoadingExperiments(false);
    }
  };

  const handleRunOptimization = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.runOptimization({
        scenario: selectedScenario,
        method: selectedMethod,
        trials: trialCount,
        random_seed: randomSeed,
        sa_iterations: saIterations,
        sa_initial_temp: initialTemp,
        sa_cooling_rate: coolingRate,
        penalty_visit: penaltyVisit,
        penalty_slot: penaltySlot,
        penalty_contig: penaltyContig,
        penalty_cap: penaltyCap,
        save_to_db: true,
        include_brute_force: includeBruteForce && selectedScenario === 'small',
        experiment_name: `Phase 5 Benchmark: ${selectedScenario.toUpperCase()} (${trialCount} Trials, Seed ${randomSeed})`
      });
      setOptimizationResult(res);
      // Auto-focus on qubo or the method executed
      if (res.methods_summary['qubo_sa']) {
        setActiveMethodTab('qubo_sa');
      } else if (res.methods_summary['classical_sa']) {
        setActiveMethodTab('classical_sa');
      } else {
        setActiveMethodTab('greedy');
      }
      loadExperiments();
    } catch (err: any) {
      setErrorMsg(err.message || 'Optimization solver failed to execute.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteExperiment = async (id: number) => {
    try {
      await api.deleteOptimizationExperiment(id);
      setExperiments((prev) => prev.filter((exp) => exp.id !== id));
      if (selectedExpDetail?.id === id) {
        setSelectedExpDetail(null);
      }
      if (optimizationResult?.experiment_id === id) {
        setOptimizationResult((prev) => (prev ? { ...prev, experiment_id: null } : null));
      }
      setSelectedForCompare((prev) => prev.filter((item) => item !== id));
    } catch (err: any) {
      setErrorMsg('Failed to delete experiment.');
    }
  };

  const handleViewExperimentDetail = async (id: number) => {
    try {
      const detail = await api.getOptimizationExperimentDetail(id);
      setSelectedExpDetail(detail);
    } catch {
      setErrorMsg('Failed to load experiment details.');
    }
  };

  const handleToggleCompare = (id: number) => {
    setSelectedForCompare((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleExecuteCompare = async () => {
    if (selectedForCompare.length < 2) return;
    try {
      const cmp = await api.compareOptimizationExperiments(selectedForCompare);
      setComparisonResults(cmp);
    } catch {
      setErrorMsg('Failed to compare selected experiments.');
    }
  };

  const handleExportJSON = () => {
    if (!optimizationResult) return;
    const blob = new Blob([JSON.stringify(optimizationResult, null, 2)], {
      type: 'application/json'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fleet_optimization_${optimizationResult.scenario_name}_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // SVG coordinate transformation helpers
  const getMapCoordinates = (points: { latitude: number; longitude: number }[]) => {
    const validPoints = (points || []).filter(
      (p) => p && typeof p.latitude === 'number' && typeof p.longitude === 'number' && !isNaN(p.latitude) && !isNaN(p.longitude)
    );
    if (validPoints.length === 0) {
      return { minLat: 12.95, maxLat: 13.15, minLon: 80.15, maxLon: 80.30 };
    }
    const lats = validPoints.map((p) => p.latitude);
    const lons = validPoints.map((p) => p.longitude);
    const minLat = Math.min(...lats) - 0.02;
    const maxLat = Math.max(...lats) + 0.02;
    const minLon = Math.min(...lons) - 0.02;
    const maxLon = Math.max(...lons) + 0.02;
    return { minLat, maxLat, minLon, maxLon };
  };

  const activeMethodSummary: MethodComparisonSummary | undefined =
    optimizationResult?.methods_summary?.[activeMethodTab];

  const allMapPoints = [
    ...(optimizationResult?.depot ? [optimizationResult.depot] : []),
    ...(optimizationResult?.destinations || [])
  ];
  const mapBounds = getMapCoordinates(allMapPoints);

  const projectToSvg = (lat: number, lon: number, width = 640, height = 360) => {
    const pad = 40;
    if (typeof lat !== 'number' || isNaN(lat) || typeof lon !== 'number' || isNaN(lon)) {
      return { x: width / 2, y: height / 2 };
    }
    const lonSpan = Math.max(1e-4, mapBounds.maxLon - mapBounds.minLon);
    const latSpan = Math.max(1e-4, mapBounds.maxLat - mapBounds.minLat);
    const x = pad + ((lon - mapBounds.minLon) / lonSpan) * (width - 2 * pad);
    const y = height - pad - ((lat - mapBounds.minLat) / latSpan) * (height - 2 * pad);
    return { x: isNaN(x) ? width / 2 : Math.round(x), y: isNaN(y) ? height / 2 : Math.round(y) };
  };

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <Compass className="apple-icon-blue" size={26} />
              <h1 className="page-title" style={{ margin: 0 }}>Fleet Optimization Lab</h1>
              <span className="apple-badge apple-badge-blue" style={{ fontSize: '0.72rem' }}>Phase 5 QUBO</span>
            </div>
            <p className="page-description" style={{ marginTop: '0.4rem', marginBottom: 0 }}>
              Rigorous comparative benchmarking of <strong>Method A (Conventional Greedy)</strong>,{' '}
              <strong>Method B (Classical Simulated Annealing)</strong>, and{' '}
              <strong>Method C (QUBO Quantum-Inspired Optimization)</strong> across multi-vehicle routing problems.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
            {optimizationResult && (
              <button
                type="button"
                className="apple-button apple-button-secondary"
                onClick={handleExportJSON}
                title="Export Experiment Record (JSON)"
              >
                <Download size={14} />
                <span>Export JSON</span>
              </button>
            )}
            <button
              id="btn-run-optimization"
              type="button"
              className="apple-button apple-button-primary"
              onClick={handleRunOptimization}
              disabled={loading}
              style={{ minWidth: '180px' }}
            >
              {loading ? (
                <>
                  <div className="apple-spinner" />
                  <span>Solving Trials...</span>
                </>
              ) : (
                <>
                  <Play size={15} />
                  <span>Run Optimization</span>
                </>
              )}
            </button>
          </div>
        </div>

        {errorMsg && (
          <div className="apple-alert apple-alert-error" style={{ marginTop: '1rem' }}>
            <AlertTriangle size={16} />
            <span>{errorMsg}</span>
          </div>
        )}
      </div>

      {/* SECTION A: Scenario & Solver Configuration */}
      <section className="apple-card" style={{ marginBottom: '1.5rem', padding: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Sliders size={18} className="apple-icon-blue" />
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>1. Scenario & Solver Parameters</h3>
          </div>
          <span style={{ fontSize: '0.75rem', color: '#64748B' }}>Deterministic seeds guarantee 100% reproducible trials</span>
        </div>

        {/* Scenario Selection Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '1.2rem' }}>
          {[
            {
              id: 'small',
              title: 'Small (Micro-Fleet)',
              sub: '2 Vehicles • 3 Waypoints',
              desc: 'State space: 2^12 = 4,096 states. Verifiable against brute-force exact oracle.',
              badge: 'Fast & Exact'
            },
            {
              id: 'medium',
              title: 'Medium (Urban Cluster)',
              sub: '3 Vehicles • 5 Waypoints',
              desc: 'State space: 2^45 ≈ 3.52×10^13 states. Evaluates route partition heuristics.',
              badge: 'Standard'
            },
            {
              id: 'large',
              title: 'Large (Regional Grid)',
              sub: '5 Vehicles • 8 Waypoints',
              desc: 'State space: 2^160 ≈ 1.46×10^48 states. Scalability test for quantum annealing.',
              badge: 'Challenging'
            }
          ].map((sc) => {
            const isSel = selectedScenario === sc.id;
            return (
              <div
                key={sc.id}
                onClick={() => setSelectedScenario(sc.id)}
                style={{
                  border: isSel ? '2px solid #2563EB' : '1px solid #E2E8F0',
                  borderRadius: '10px',
                  padding: '1rem',
                  cursor: 'pointer',
                  backgroundColor: isSel ? '#F8FAFC' : '#FFFFFF',
                  boxShadow: isSel ? '0 2px 8px rgba(37,99,235,0.12)' : 'none',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.9rem', color: isSel ? '#1E293B' : '#475569' }}>{sc.title}</span>
                  <span className={`apple-badge ${isSel ? 'apple-badge-blue' : 'apple-badge-gray'}`} style={{ fontSize: '0.68rem' }}>{sc.badge}</span>
                </div>
                <div style={{ fontSize: '0.8rem', color: '#2563EB', fontWeight: 500, marginBottom: '0.3rem' }}>{sc.sub}</div>
                <div style={{ fontSize: '0.75rem', color: '#64748B', lineHeight: '1.3' }}>{sc.desc}</div>
              </div>
            );
          })}
        </div>

        {/* Hyperparameters Controls */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', paddingTop: '0.5rem', borderTop: '1px solid #F1F5F9' }}>
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '0.3rem' }}>
              Independent Trials (K)
            </label>
            <input
              type="number"
              min={1}
              max={30}
              value={trialCount}
              onChange={(e) => setTrialCount(Math.max(1, Math.min(30, parseInt(e.target.value) || 1)))}
              className="apple-input"
              style={{ width: '100%', fontSize: '0.85rem' }}
            />
            <span style={{ fontSize: '0.7rem', color: '#94A3B8' }}>Up to 30 trials per run</span>
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '0.3rem' }}>
              Random Seed
            </label>
            <input
              type="number"
              value={randomSeed}
              onChange={(e) => setRandomSeed(parseInt(e.target.value) || 42)}
              className="apple-input"
              style={{ width: '100%', fontSize: '0.85rem' }}
            />
            <span style={{ fontSize: '0.7rem', color: '#94A3B8' }}>Seed_k = Seed + k</span>
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '0.3rem' }}>
              SA Iterations
            </label>
            <input
              type="number"
              step={100}
              min={100}
              max={5000}
              value={saIterations}
              onChange={(e) => setSaIterations(parseInt(e.target.value) || 1000)}
              className="apple-input"
              style={{ width: '100%', fontSize: '0.85rem' }}
            />
            <span style={{ fontSize: '0.7rem', color: '#94A3B8' }}>Metropolis sample steps</span>
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '0.3rem' }}>
              Cooling Rate (α)
            </label>
            <input
              type="number"
              step={0.005}
              min={0.8}
              max={0.999}
              value={coolingRate}
              onChange={(e) => setCoolingRate(parseFloat(e.target.value) || 0.985)}
              className="apple-input"
              style={{ width: '100%', fontSize: '0.85rem' }}
            />
            <span style={{ fontSize: '0.7rem', color: '#94A3B8' }}>T_(k+1) = α * T_k</span>
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '0.3rem' }}>
              Penalty Mult. (P_A / P_B)
            </label>
            <div style={{ display: 'flex', gap: '0.4rem' }}>
              <input
                type="number"
                value={penaltyVisit}
                onChange={(e) => setPenaltyVisit(parseFloat(e.target.value) || 150.0)}
                className="apple-input"
                style={{ width: '50%', fontSize: '0.85rem' }}
                title="Visit Penalty P_A"
              />
              <input
                type="number"
                value={penaltySlot}
                onChange={(e) => setPenaltySlot(parseFloat(e.target.value) || 120.0)}
                className="apple-input"
                style={{ width: '50%', fontSize: '0.85rem' }}
                title="Slot Penalty P_B"
              />
            </div>
            <span style={{ fontSize: '0.7rem', color: '#94A3B8' }}>P_A (visit) / P_B (slot)</span>
          </div>
        </div>

        {/* Brute Force Checkbox */}
        {selectedScenario === 'small' && (
          <div style={{ marginTop: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              id="chk-brute-force"
              checked={includeBruteForce}
              onChange={(e) => setIncludeBruteForce(e.target.checked)}
              style={{ cursor: 'pointer' }}
            />
            <label htmlFor="chk-brute-force" style={{ fontSize: '0.8rem', color: '#334155', cursor: 'pointer', fontWeight: 500 }}>
              Include Mathematical Ground-Truth (Exact Exhaustive Brute-Force across all 4,096 states)
            </label>
          </div>
        )}
      </section>

      {/* SECTION B: Three Methods Side-by-Side Comparison */}
      {optimizationResult && (
        <section className="apple-card" style={{ marginBottom: '1.5rem', padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <GitCompare size={18} className="apple-icon-blue" />
              <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>2. Methodological Benchmark Comparison</h3>
            </div>
            <span style={{ fontSize: '0.75rem', color: '#64748B' }}>
              Scenario: <strong>{optimizationResult.scenario_name.toUpperCase()}</strong> ({optimizationResult.vehicle_count} Vehicles, {optimizationResult.destination_count} Destinations, {optimizationResult.trials.length} Total Executions)
            </span>
          </div>

          {/* Comparative Metrics Table */}
          <div style={{ overflowX: 'auto', marginBottom: '1.2rem' }}>
            <table className="apple-table" style={{ width: '100%', fontSize: '0.85rem' }}>
              <thead>
                <tr>
                  <th>Method</th>
                  <th>Feasibility</th>
                  <th>Best Obj</th>
                  <th>Mean Obj ± Std</th>
                  <th>Mean Distance</th>
                  <th>Mean Travel Time</th>
                  <th>Median Runtime</th>
                  <th>P95 Runtime</th>
                  <th>Constraint Violations</th>
                </tr>
              </thead>
              <tbody>
                {/* Method A */}
                {optimizationResult.methods_summary['greedy'] && (
                  <tr style={{ backgroundColor: activeMethodTab === 'greedy' ? '#F1F5F9' : 'transparent' }}>
                    <td>
                      <button
                        type="button"
                        onClick={() => setActiveMethodTab('greedy')}
                        style={{ border: 'none', background: 'none', color: '#2563EB', fontWeight: 600, cursor: 'pointer', textAlign: 'left' }}
                      >
                        Method A — Conventional Greedy Baseline
                      </button>
                    </td>
                    <td>
                      <span className={`apple-badge ${optimizationResult.methods_summary['greedy'].feasibility_percentage === 100 ? 'apple-badge-green' : 'apple-badge-red'}`}>
                        {optimizationResult.methods_summary['greedy'].feasibility_percentage}%
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{optimizationResult.methods_summary['greedy'].best_objective.toFixed(2)}</td>
                    <td>{optimizationResult.methods_summary['greedy'].mean_objective.toFixed(2)} ± {optimizationResult.methods_summary['greedy'].std_objective.toFixed(2)}</td>
                    <td>{optimizationResult.methods_summary['greedy'].mean_distance_km.toFixed(2)} km</td>
                    <td>{optimizationResult.methods_summary['greedy'].mean_travel_time_min.toFixed(1)} min</td>
                    <td>{optimizationResult.methods_summary['greedy'].median_runtime_ms.toFixed(2)} ms</td>
                    <td>{optimizationResult.methods_summary['greedy'].p95_runtime_ms.toFixed(2)} ms</td>
                    <td>{optimizationResult.methods_summary['greedy'].mean_violations.toFixed(1)}</td>
                  </tr>
                )}

                {/* Method B */}
                {optimizationResult.methods_summary['classical_sa'] && (
                  <tr style={{ backgroundColor: activeMethodTab === 'classical_sa' ? '#F1F5F9' : 'transparent' }}>
                    <td>
                      <button
                        type="button"
                        onClick={() => setActiveMethodTab('classical_sa')}
                        style={{ border: 'none', background: 'none', color: '#7C3AED', fontWeight: 600, cursor: 'pointer', textAlign: 'left' }}
                      >
                        Method B — Classical Simulated Annealing
                      </button>
                    </td>
                    <td>
                      <span className={`apple-badge ${optimizationResult.methods_summary['classical_sa'].feasibility_percentage === 100 ? 'apple-badge-green' : 'apple-badge-red'}`}>
                        {optimizationResult.methods_summary['classical_sa'].feasibility_percentage}%
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{optimizationResult.methods_summary['classical_sa'].best_objective.toFixed(2)}</td>
                    <td>{optimizationResult.methods_summary['classical_sa'].mean_objective.toFixed(2)} ± {optimizationResult.methods_summary['classical_sa'].std_objective.toFixed(2)}</td>
                    <td>{optimizationResult.methods_summary['classical_sa'].mean_distance_km.toFixed(2)} km</td>
                    <td>{optimizationResult.methods_summary['classical_sa'].mean_travel_time_min.toFixed(1)} min</td>
                    <td>{optimizationResult.methods_summary['classical_sa'].median_runtime_ms.toFixed(2)} ms</td>
                    <td>{optimizationResult.methods_summary['classical_sa'].p95_runtime_ms.toFixed(2)} ms</td>
                    <td>{optimizationResult.methods_summary['classical_sa'].mean_violations.toFixed(1)}</td>
                  </tr>
                )}

                {/* Method C */}
                {optimizationResult.methods_summary['qubo_sa'] && (
                  <tr style={{ backgroundColor: activeMethodTab === 'qubo_sa' ? '#F1F5F9' : 'transparent' }}>
                    <td>
                      <button
                        type="button"
                        onClick={() => setActiveMethodTab('qubo_sa')}
                        style={{ border: 'none', background: 'none', color: '#059669', fontWeight: 600, cursor: 'pointer', textAlign: 'left' }}
                      >
                        Method C — QUBO + Simulated Annealing Solver
                      </button>
                    </td>
                    <td>
                      <span className={`apple-badge ${optimizationResult.methods_summary['qubo_sa'].feasibility_percentage === 100 ? 'apple-badge-green' : 'apple-badge-red'}`}>
                        {optimizationResult.methods_summary['qubo_sa'].feasibility_percentage}%
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{optimizationResult.methods_summary['qubo_sa'].best_objective.toFixed(2)}</td>
                    <td>{optimizationResult.methods_summary['qubo_sa'].mean_objective.toFixed(2)} ± {optimizationResult.methods_summary['qubo_sa'].std_objective.toFixed(2)}</td>
                    <td>{optimizationResult.methods_summary['qubo_sa'].mean_distance_km.toFixed(2)} km</td>
                    <td>{optimizationResult.methods_summary['qubo_sa'].mean_travel_time_min.toFixed(1)} min</td>
                    <td>{optimizationResult.methods_summary['qubo_sa'].median_runtime_ms.toFixed(2)} ms</td>
                    <td>{optimizationResult.methods_summary['qubo_sa'].p95_runtime_ms.toFixed(2)} ms</td>
                    <td>{optimizationResult.methods_summary['qubo_sa'].mean_violations.toFixed(1)}</td>
                  </tr>
                )}

                {/* Brute Force Exact Oracle */}
                {optimizationResult.brute_force_exact && (
                  <tr style={{ backgroundColor: '#F8FAFC', fontStyle: 'italic' }}>
                    <td>
                      <span style={{ fontWeight: 600, color: '#0F172A' }}>★ Exact Oracle (Exhaustive Brute-Force)</span>
                    </td>
                    <td>
                      <span className="apple-badge apple-badge-green">100%</span>
                    </td>
                    <td style={{ fontWeight: 700 }}>{optimizationResult.brute_force_exact.min_qubo_energy.toFixed(2)}</td>
                    <td>{optimizationResult.brute_force_exact.total_distance_km.toFixed(2)} (Global Optimum)</td>
                    <td>{optimizationResult.brute_force_exact.total_distance_km.toFixed(2)} km</td>
                    <td>{(optimizationResult.brute_force_exact.total_distance_km * 1.5).toFixed(1)} min</td>
                    <td>{optimizationResult.brute_force_exact.execution_time_ms.toFixed(2)} ms</td>
                    <td>{optimizationResult.brute_force_exact.execution_time_ms.toFixed(2)} ms</td>
                    <td>0</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Method View Selector Tabs */}
          <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid #E2E8F0', paddingBottom: '0.5rem' }}>
            {optimizationResult.methods_summary['qubo_sa'] && (
              <button
                type="button"
                className={`apple-button ${activeMethodTab === 'qubo_sa' ? 'apple-button-primary' : 'apple-button-secondary'}`}
                style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                onClick={() => setActiveMethodTab('qubo_sa')}
              >
                Inspect Method C (QUBO / SA)
              </button>
            )}
            {optimizationResult.methods_summary['classical_sa'] && (
              <button
                type="button"
                className={`apple-button ${activeMethodTab === 'classical_sa' ? 'apple-button-primary' : 'apple-button-secondary'}`}
                style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                onClick={() => setActiveMethodTab('classical_sa')}
              >
                Inspect Method B (Classical SA)
              </button>
            )}
            {optimizationResult.methods_summary['greedy'] && (
              <button
                type="button"
                className={`apple-button ${activeMethodTab === 'greedy' ? 'apple-button-primary' : 'apple-button-secondary'}`}
                style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                onClick={() => setActiveMethodTab('greedy')}
              >
                Inspect Method A (Greedy)
              </button>
            )}
          </div>
        </section>
      )}

      {/* SECTION C & D: KPI Dashboard & Visual Comparison */}
      {activeMethodSummary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.2rem', marginBottom: '1.5rem' }}>
          {/* Key Metrics Card */}
          <div className="apple-card" style={{ padding: '1.25rem' }}>
            <h4 style={{ margin: '0 0 1rem 0', fontSize: '0.9rem', color: '#475569' }}>
              Performance Summary — {activeMethodSummary.method_name}
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
              <div style={{ backgroundColor: '#F8FAFC', padding: '0.75rem', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.7rem', color: '#64748B' }}>Total Route Distance</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0F172A' }}>
                  {activeMethodSummary.mean_distance_km.toFixed(2)} <span style={{ fontSize: '0.75rem' }}>km</span>
                </div>
              </div>
              <div style={{ backgroundColor: '#F8FAFC', padding: '0.75rem', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.7rem', color: '#64748B' }}>Estimated Travel Time</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0F172A' }}>
                  {activeMethodSummary.mean_travel_time_min.toFixed(0)} <span style={{ fontSize: '0.75rem' }}>min</span>
                </div>
              </div>
              <div style={{ backgroundColor: '#F8FAFC', padding: '0.75rem', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.7rem', color: '#64748B' }}>Median Runtime</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0F172A' }}>
                  {activeMethodSummary.median_runtime_ms.toFixed(2)} <span style={{ fontSize: '0.75rem' }}>ms</span>
                </div>
              </div>
              <div style={{ backgroundColor: '#F8FAFC', padding: '0.75rem', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.7rem', color: '#64748B' }}>Feasibility Rate</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: activeMethodSummary.feasibility_percentage === 100 ? '#059669' : '#DC2626' }}>
                  {activeMethodSummary.feasibility_percentage}%
                </div>
              </div>
            </div>

            <div style={{ marginTop: '0.8rem', fontSize: '0.75rem', color: '#64748B' }}>
              Best Objective: <strong>{activeMethodSummary.best_objective.toFixed(2)}</strong> | P95 Runtime: <strong>{activeMethodSummary.p95_runtime_ms.toFixed(2)} ms</strong>
            </div>
          </div>

          {/* Convergence History Visualizer (when available) */}
          <div className="apple-card" style={{ padding: '1.25rem' }}>
            <h4 style={{ margin: '0 0 1rem 0', fontSize: '0.9rem', color: '#475569' }}>
              Energy Convergence History ({activeMethodSummary.convergence_history?.length || 0} Sample Points)
            </h4>
            {activeMethodSummary.convergence_history && activeMethodSummary.convergence_history.length > 0 ? (
              <div style={{ height: '140px', display: 'flex', alignItems: 'flex-end', gap: '3px', padding: '0.5rem 0', borderBottom: '1px solid #CBD5E1' }}>
                {activeMethodSummary.convergence_history.map((step, idx) => {
                  const maxE = Math.max(...activeMethodSummary.convergence_history!.map((s) => s.best_energy), 1);
                  const minE = Math.min(...activeMethodSummary.convergence_history!.map((s) => s.best_energy), 0);
                  const range = Math.max(1e-4, maxE - minE);
                  const barHeight = Math.max(10, Math.round(((step.best_energy - minE) / range) * 110));
                  return (
                    <div
                      key={idx}
                      title={`Iteration ${step.iteration}: Best Energy = ${step.best_energy.toFixed(2)}, Temp = ${step.temperature.toFixed(2)}`}
                      style={{
                        flex: 1,
                        backgroundColor: '#2563EB',
                        height: `${barHeight}px`,
                        borderRadius: '2px 2px 0 0',
                        opacity: 0.75,
                        transition: 'height 0.2s ease'
                      }}
                    />
                  );
                })}
              </div>
            ) : (
              <div style={{ height: '140px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94A3B8', fontSize: '0.8rem' }}>
                Deterministic Greedy baseline does not require iterative stochastic sampling.
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#94A3B8', marginTop: '0.4rem' }}>
              <span>Initial Temp: {initialTemp}°</span>
              <span>Final Temp: {(initialTemp * Math.pow(coolingRate, saIterations)).toFixed(2)}°</span>
            </div>
          </div>
        </div>
      )}

      {/* SECTION E: Route Visualization on Leaflet Map Canvas */}
      {activeMethodSummary && (
        <section className="apple-card" style={{ marginBottom: '1.5rem', padding: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Layers size={18} className="apple-icon-blue" />
              <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>3. Chennai Fleet Routing Geometry</h3>
            </div>
            <div style={{ fontSize: '0.75rem', color: '#64748B' }}>
              Displaying Best Solution for: <strong>{activeMethodSummary.method_name}</strong>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 1.8fr) minmax(260px, 1.2fr)', gap: '1.2rem' }}>
            {/* SVG Visual Map Canvas */}
            <div style={{ backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '10px', padding: '0.5rem', position: 'relative' }}>
              <svg width="100%" height="360" viewBox="0 0 640 360" style={{ display: 'block' }}>
                {/* Background grid */}
                <defs>
                  <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#E2E8F0" strokeWidth="0.8" />
                  </pattern>
                </defs>
                <rect width="640" height="360" fill="url(#grid)" />

                {/* Vehicle route polylines */}
                {activeMethodSummary.best_solution_routes.map((vr, vIdx) => {
                  const color = routeColors[vIdx % routeColors.length];
                  const points = vr.stop_sequence.map((stop) => {
                    const coord = projectToSvg(stop.latitude, stop.longitude);
                    return `${coord.x},${coord.y}`;
                  }).join(' ');

                  return (
                    <g key={vr.vehicle_id}>
                      <polyline
                        points={points}
                        fill="none"
                        stroke={color}
                        strokeWidth="2.5"
                        strokeDasharray={vIdx % 2 === 1 ? '4 2' : 'none'}
                        opacity="0.85"
                      />
                    </g>
                  );
                })}

                {/* Waypoint nodes */}
                {optimizationResult?.destinations.map((wp) => {
                  const pt = projectToSvg(wp.latitude, wp.longitude);
                  return (
                    <g key={wp.id} transform={`translate(${pt.x}, ${pt.y})`}>
                      <circle r="7" fill="#2563EB" stroke="#FFFFFF" strokeWidth="2" />
                      <text x="10" y="4" fontSize="10" fill="#1E293B" fontWeight="600">
                        {wp.name} ({wp.demand}kg)
                      </text>
                    </g>
                  );
                })}

                {/* Depot Node */}
                {optimizationResult?.depot && (() => {
                  const dpt = projectToSvg(optimizationResult.depot.latitude, optimizationResult.depot.longitude);
                  return (
                    <g transform={`translate(${dpt.x}, ${dpt.y})`}>
                      <rect x="-9" y="-9" width="18" height="18" rx="3" fill="#DC2626" stroke="#FFFFFF" strokeWidth="2" />
                      <text x="12" y="4" fontSize="11" fill="#DC2626" fontWeight="700">
                        Central Logistics Depot
                      </text>
                    </g>
                  );
                })()}
              </svg>
            </div>

            {/* Vehicle Route Details */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', maxHeight: '360px', overflowY: 'auto' }}>
              {activeMethodSummary.best_solution_routes.map((route, idx) => {
                const color = routeColors[idx % routeColors.length];
                return (
                  <div
                    key={route.vehicle_id}
                    style={{
                      borderLeft: `4px solid ${color}`,
                      backgroundColor: '#FFFFFF',
                      border: '1px solid #E2E8F0',
                      borderLeftWidth: '4px',
                      borderRadius: '8px',
                      padding: '0.75rem'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.85rem', color: '#1E293B' }}>{route.vehicle_name}</span>
                      <span className={`apple-badge ${route.feasible ? 'apple-badge-green' : 'apple-badge-red'}`} style={{ fontSize: '0.68rem' }}>
                        {route.feasible ? 'Feasible' : 'Overcapacity'}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#64748B', marginBottom: '0.4rem' }}>
                      Distance: <strong>{route.total_distance_km.toFixed(2)} km</strong> • Load: <strong>{route.total_demand_delivered} kg</strong> ({route.capacity_utilized_percent}%)
                    </div>
                    <div style={{ fontSize: '0.7rem', color: '#475569', lineHeight: '1.4' }}>
                      <strong>Stops:</strong>{' '}
                      {route.stop_sequence.map((s, sIdx) => (
                        <span key={sIdx}>
                          {s.name}
                          {sIdx < route.stop_sequence.length - 1 ? ' → ' : ''}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      )}

      {/* SECTION F: Historical Experiments Table & Comparison Drawer */}
      <section className="apple-card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Clock size={18} className="apple-icon-blue" />
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>4. Experiment History & Side-by-Side Comparison</h3>
          </div>
          {selectedForCompare.length >= 2 && (
            <button
              type="button"
              className="apple-button apple-button-primary"
              style={{ fontSize: '0.8rem', padding: '0.35rem 0.8rem' }}
              onClick={handleExecuteCompare}
            >
              <GitCompare size={14} />
              <span>Compare Selected ({selectedForCompare.length})</span>
            </button>
          )}
        </div>

        {/* Experiments Table */}
        <div style={{ overflowX: 'auto' }}>
          <table className="apple-table" style={{ width: '100%', fontSize: '0.82rem' }}>
            <thead>
              <tr>
                <th style={{ width: '35px' }}>Comp</th>
                <th>ID</th>
                <th>Experiment Name</th>
                <th>Scenario</th>
                <th>Vehicles</th>
                <th>Destinations</th>
                <th>Objective Value</th>
                <th>Distance</th>
                <th>Status</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {experiments.length === 0 ? (
                <tr>
                  <td colSpan={11} style={{ textAlign: 'center', color: '#94A3B8', padding: '1.5rem' }}>
                    {loadingExperiments ? 'Loading historical optimization records...' : 'No historical experiments found. Run a new optimization above to persist benchmark data.'}
                  </td>
                </tr>
              ) : (
                experiments.map((exp) => (
                  <tr key={exp.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedForCompare.includes(exp.id)}
                        onChange={() => handleToggleCompare(exp.id)}
                      />
                    </td>
                    <td>#{exp.id}</td>
                    <td style={{ fontWeight: 500 }}>{exp.experiment_name}</td>
                    <td>
                      <span className="apple-badge apple-badge-gray" style={{ textTransform: 'uppercase', fontSize: '0.68rem' }}>
                        {exp.scenario_name}
                      </span>
                    </td>
                    <td>{exp.vehicle_count}</td>
                    <td>{exp.destination_count}</td>
                    <td style={{ fontWeight: 600 }}>{exp.objective_value ? exp.objective_value.toFixed(2) : '—'}</td>
                    <td>{exp.total_distance ? `${exp.total_distance.toFixed(1)} km` : '—'}</td>
                    <td>
                      <span className={`apple-badge ${exp.feasibility_status ? 'apple-badge-green' : 'apple-badge-red'}`} style={{ fontSize: '0.68rem' }}>
                        {exp.feasibility_status ? 'Feasible' : 'Violations'}
                      </span>
                    </td>
                    <td>{new Date(exp.created_at).toLocaleString()}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.4rem' }}>
                        <button
                          type="button"
                          className="apple-button apple-button-secondary"
                          style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem' }}
                          onClick={() => handleViewExperimentDetail(exp.id)}
                          title="Inspect trial records"
                        >
                          <Eye size={12} />
                        </button>
                        <button
                          type="button"
                          className="apple-button apple-button-secondary"
                          style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem', color: '#DC2626' }}
                          onClick={() => handleDeleteExperiment(exp.id)}
                          title="Delete experiment"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Selected Experiment Detail Modal / Card */}
        {selectedExpDetail && (
          <div style={{ marginTop: '1.2rem', padding: '1rem', backgroundColor: '#F8FAFC', borderRadius: '8px', border: '1px solid #CBD5E1' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
              <h4 style={{ margin: 0, fontSize: '0.9rem', color: '#1E293B' }}>
                Experiment #{selectedExpDetail.id} Breakdown: {selectedExpDetail.experiment_name}
              </h4>
              <button
                type="button"
                className="apple-button apple-button-secondary"
                style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem' }}
                onClick={() => setSelectedExpDetail(null)}
              >
                Close
              </button>
            </div>
            <div style={{ fontSize: '0.78rem', color: '#475569', marginBottom: '0.8rem' }}>
              Recorded Trials: <strong>{selectedExpDetail.trials?.length || 0}</strong> • Seed: <strong>{selectedExpDetail.random_seed}</strong> • Objective: <strong>{selectedExpDetail.objective_value?.toFixed(2)}</strong>
            </div>

            {/* Trial Rows */}
            <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
              <table className="apple-table" style={{ width: '100%', fontSize: '0.75rem' }}>
                <thead>
                  <tr>
                    <th>Trial</th>
                    <th>Method</th>
                    <th>Objective</th>
                    <th>Distance</th>
                    <th>Runtime</th>
                    <th>Feasible</th>
                    <th>Violations</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedExpDetail.trials?.map((tr: any) => (
                    <tr key={tr.id}>
                      <td>#{tr.trial_number}</td>
                      <td style={{ fontWeight: 600 }}>{tr.method}</td>
                      <td>{tr.objective_value.toFixed(2)}</td>
                      <td>{tr.total_distance.toFixed(2)} km</td>
                      <td>{tr.execution_time_ms.toFixed(2)} ms</td>
                      <td>{tr.feasibility_status ? 'Yes' : 'No'}</td>
                      <td>{tr.constraint_violations}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Multi-Experiment Comparative Modal / Card */}
        {comparisonResults && (
          <div style={{ marginTop: '1.2rem', padding: '1rem', backgroundColor: '#EFF6FF', borderRadius: '8px', border: '1px solid #BFDBFE' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
              <h4 style={{ margin: 0, fontSize: '0.9rem', color: '#1E3A8A' }}>
                Side-by-Side Comparison of {comparisonResults.length} Experiments
              </h4>
              <button
                type="button"
                className="apple-button apple-button-secondary"
                style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem' }}
                onClick={() => setComparisonResults(null)}
              >
                Close Comparison
              </button>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="apple-table" style={{ width: '100%', fontSize: '0.78rem' }}>
                <thead>
                  <tr>
                    <th>Exp ID</th>
                    <th>Name</th>
                    <th>Scenario</th>
                    <th>Vehicles</th>
                    <th>Destinations</th>
                    <th>Best Obj</th>
                    <th>Distance</th>
                    <th>Runtime</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonResults.map((c) => (
                    <tr key={c.id}>
                      <td>#{c.id}</td>
                      <td style={{ fontWeight: 500 }}>{c.experiment_name}</td>
                      <td>{c.scenario_name}</td>
                      <td>{c.vehicle_count}</td>
                      <td>{c.destination_count}</td>
                      <td style={{ fontWeight: 600 }}>{c.objective_value?.toFixed(2)}</td>
                      <td>{c.total_distance?.toFixed(2)} km</td>
                      <td>{c.execution_time_ms?.toFixed(2)} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  );
};

export default QuboRoutingPage;
