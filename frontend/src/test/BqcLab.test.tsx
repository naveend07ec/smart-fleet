import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BqcLabPage } from '../pages/BqcLabPage';
import { api } from '../services/api';

vi.mock('../services/api', () => ({
  api: {
    getBqcStatus: vi.fn(),
    demonstrateBqc: vi.fn(),
    runBqcBatchTrials: vi.fn(),
    getBqcExperiments: vi.fn(),
  },
}));

// Mock react-chartjs-2 to avoid canvas issues in jsdom
vi.mock('react-chartjs-2', () => ({
  Bar: () => <div data-testid="mock-bar-chart">Latency Distribution Chart</div>,
}));

describe('BqcLabPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (api.getBqcStatus as any).mockResolvedValue({
      status: 'operational',
      protocol: 'BFK09 Universal Blind Quantum Computing',
      quantum_simulator: 'Local Classical State Vector Simulator',
      max_qubits_supported: 16,
      client_model: 'Simulated single-qubit preparation client',
      server_model: 'Simulated untrusted quantum server',
      cluster_topologies: {
        'linear-4': '4-qubit linear cluster',
        'ladder-6': '6-qubit ladder cluster'
      },
      research_disclaimer: 'Classical software simulation. No physical quantum hardware or quantum advantage.'
    });

    (api.getBqcExperiments as any).mockResolvedValue([
      {
        id: 1,
        name: 'BFK09 Fleet Optimization M=2',
        num_candidates: 2,
        num_qubits: 4,
        cluster_topology: 'linear',
        created_at: new Date().toISOString(),
        total_trials: 20,
        correctness_rate: 100.0
      }
    ]);

    (api.demonstrateBqc as any).mockResolvedValue({
      num_candidates: 2,
      candidate_names: ['North Depot', 'South Depot'],
      mode_a: {
        mode: 'mode_a',
        num_candidates: 2,
        selected_depot_index: 0,
        selected_depot_name: 'North Depot',
        selected_cost: 12.5,
        all_costs: [12.5, 24.0],
        execution_time_ms: 0.42,
        wire_bytes: 140,
        server_visibility: 'Plaintext',
        privacy_guarantee: 'None',
        server_learned_gps: true,
        server_learned_costs: true,
        server_learned_output: true
      },
      mode_b: {
        mode: 'mode_b',
        num_candidates: 2,
        num_qubits: 4,
        cluster_topology: 'linear',
        graph_edges: [[0, 1], [1, 2], [2, 3]],
        selected_depot_index: 0,
        selected_depot_name: 'North Depot',
        selected_cost: 12.5,
        all_costs: [12.5, 24.0],
        classical_min_index: 0,
        correctness: true,
        client_prep_ms: 3.2,
        server_quantum_ms: 8.5,
        total_execution_ms: 11.7,
        client_to_server_bytes: 420,
        server_to_client_bytes: 428,
        total_wire_bytes: 848,
        blinded_angles_rad: [0.785, 3.141, 1.571, 4.712],
        server_raw_outcomes: [0, 1, 0, 1],
        client_unpadded_outcomes: [0, 0, 1, 0],
        angle_entropy_bits: 3.0,
        max_theoretical_entropy: 3.0,
        server_visibility: 'Universal Blindness',
        privacy_guarantee: 'Universal Blind Quantum Computing (BFK09)',
        server_learned_gps: false,
        server_learned_costs: false,
        server_learned_output: false,
        diagnostics: {},
        server_visibility_audit: {
          server_received_qubits: 4,
          server_received_angles_count: 4,
          server_observed_angles_sample: [0.785, 3.141],
          server_observed_raw_outcomes: [0, 1],
          server_learned_gps: false,
          server_learned_costs: false,
          server_learned_target_depot: false,
          total_bytes_received: 420,
          total_bytes_sent: 428
        }
      },
      correctness_verified: true,
      wire_expansion_percent: 505.7,
      privacy_contrast: {}
    });

    (api.runBqcBatchTrials as any).mockResolvedValue({
      experiment_id: 2,
      num_candidates: 2,
      trials_executed_per_mode: 10,
      mode_a: {
        median_latency_ms: 0.38,
        mean_latency_ms: 0.41,
        p95_latency_ms: 0.55,
        min_latency_ms: 0.31,
        max_latency_ms: 0.62,
        mean_wire_bytes: 140.0
      },
      mode_b: {
        median_latency_ms: 12.1,
        mean_latency_ms: 12.8,
        p95_latency_ms: 15.4,
        min_latency_ms: 10.5,
        max_latency_ms: 16.2,
        mean_wire_bytes: 848.0
      },
      wire_expansion_percent: 505.7,
      algorithmic_correctness_rate: 100.0,
      universal_blindness_verified_rate: 100.0,
      mean_angle_entropy_bits: 2.98,
      total_variation_distance: 0.045,
      distinguishability_verdict: 'Statistically Indistinguishable (Universal Blindness Preserved)'
    });
  });

  it('renders page header, scientific disclaimer, and protocol status cards', async () => {
    render(<BqcLabPage />);

    expect(screen.getByText(/Blind Quantum Computing \(BQC\) Privacy Lab/i)).toBeInTheDocument();
    expect(screen.getByText(/Scientific & Simulator Disclaimer/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Universal Blindness/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Theoretical Angle Entropy/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/#1/i)).toBeInTheDocument();
      expect(screen.getByText(/BFK09 Fleet Optimization M=2/i)).toBeInTheDocument();
    });
  });

  it('renders SVG cluster state for M=2', () => {
    render(<BqcLabPage />);
    const svgElem = document.getElementById('cluster-svg-m2');
    expect(svgElem).toBeInTheDocument();
  });

  it('runs demonstration and displays side-by-side contrast', async () => {
    render(<BqcLabPage />);

    const runBtn = screen.getByRole('button', { name: /Run Comparative Protocol Demonstration/i });
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(api.demonstrateBqc).toHaveBeenCalledWith({
        num_candidates: 2,
        cluster_topology: 'linear'
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/Side-by-Side Security & Execution Contrast/i)).toBeInTheDocument();
      expect(screen.getByText(/Mode A: Classical Baseline/i)).toBeInTheDocument();
      expect(screen.getByText(/Mode B: BFK09 Delegated BQC/i)).toBeInTheDocument();
      expect(screen.getByText(/Server-Observable Information Inspector/i)).toBeInTheDocument();
    });
  });

  it('runs batch trials and displays KPI verification stats', async () => {
    render(<BqcLabPage />);

    const batchBtn = screen.getByRole('button', { name: /Execute 20 Batch Trials/i });
    fireEvent.click(batchBtn);

    await waitFor(() => {
      expect(api.runBqcBatchTrials).toHaveBeenCalledWith({
        num_candidates: 2,
        trials_per_mode: 10,
        cluster_topology: 'linear'
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/Algorithmic Correctness:/i)).toBeInTheDocument();
      expect(screen.getByText(/Statistically Indistinguishable \(Universal Blindness Preserved\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Total Variation Distance \(TVD\):/i)).toBeInTheDocument();
    });
  });
});
