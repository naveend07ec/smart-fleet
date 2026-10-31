import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QuboRoutingPage } from '../pages/QuboRoutingPage';
import { api } from '../services/api';

vi.mock('../services/api', () => ({
  api: {
    getOptimizationScenarios: vi.fn(),
    getOptimizationExperiments: vi.fn(),
    runOptimization: vi.fn(),
    getOptimizationExperimentDetail: vi.fn(),
    deleteOptimizationExperiment: vi.fn(),
    compareOptimizationExperiments: vi.fn(),
    getRoutingDefaults: vi.fn(),
    getRoutingExperiments: vi.fn(),
    optimizeRoutes: vi.fn(),
    deleteRoutingExperiment: vi.fn(),
  },
}));

describe('Fleet Optimization Lab (QuboRoutingPage) Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.getOptimizationScenarios as any).mockResolvedValue([
      {
        id: 'small',
        name: 'Small (Micro-Fleet)',
        description: '2 vehicles, 3 waypoints',
        vehicle_count: 2,
        destination_count: 3,
        max_steps: 2,
        num_qubo_variables: 12,
        state_space_size: '2^12 = 4,096',
        depot: { id: 'depot-central', name: 'Central Logistics Hub', latitude: 13.0827, longitude: 80.2707 },
        vehicles: [
          { id: 'EV-01', name: 'Alpha Electric Van', capacity: 65, battery_range_km: 95.0, energy_rate_kwh_per_km: 0.22 },
          { id: 'EV-02', name: 'Beta Electric Van', capacity: 65, battery_range_km: 95.0, energy_rate_kwh_per_km: 0.22 },
        ],
        destinations: [
          { id: 'wp-1', name: 'T. Nagar Hub', latitude: 13.0418, longitude: 80.2341, demand: 15, priority: 2 },
          { id: 'wp-2', name: 'Adyar Terminal', latitude: 13.0067, longitude: 80.2570, demand: 12, priority: 1 },
          { id: 'wp-3', name: 'Anna Nagar North', latitude: 13.0850, longitude: 80.2100, demand: 18, priority: 3 },
        ]
      }
    ]);
    (api.getOptimizationExperiments as any).mockResolvedValue([]);
  });

  it('renders page titles, scenario parameters, and initial empty history state', async () => {
    render(<QuboRoutingPage />);

    expect(screen.getByText('Fleet Optimization Lab')).toBeInTheDocument();
    expect(screen.getByText(/Phase 5 QUBO/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Run Optimization/i })).toBeInTheDocument();
    expect(screen.getByText(/Scenario & Solver Parameters/i)).toBeInTheDocument();
    expect(screen.getByText(/Small \(Micro-Fleet\)/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/No historical experiments found/i)).toBeInTheDocument();
    });
  });

  it('triggers optimization solver and renders three-method benchmark results', async () => {
    (api.runOptimization as any).mockResolvedValue({
      experiment_id: 201,
      experiment_name: 'Phase 5 Benchmark: SMALL (3 Trials, Seed 42)',
      scenario_name: 'small',
      vehicle_count: 2,
      destination_count: 3,
      method: 'all_comparative',
      random_seed: 42,
      solver_parameters: {
        trials: 3,
        sa_iterations: 1000,
        sa_initial_temp: 100.0,
        sa_cooling_rate: 0.985,
        penalty_visit: 150.0,
        penalty_slot: 120.0,
        penalty_contig: 80.0,
        penalty_cap: 100.0,
        max_steps: 2,
        num_qubo_variables: 12
      },
      depot: { id: 'depot-central', name: 'Central Logistics Hub', latitude: 13.0827, longitude: 80.2707 },
      destinations: [
        { id: 'wp-1', name: 'T. Nagar Hub', latitude: 13.0418, longitude: 80.2341, demand: 15, priority: 2 },
        { id: 'wp-2', name: 'Adyar Terminal', latitude: 13.0067, longitude: 80.2570, demand: 12, priority: 1 },
        { id: 'wp-3', name: 'Anna Nagar North', latitude: 13.0850, longitude: 80.2100, demand: 18, priority: 3 }
      ],
      vehicles: [
        { id: 'EV-01', name: 'Alpha Electric Van', capacity: 65, battery_range_km: 95.0, energy_rate_kwh_per_km: 0.22 },
        { id: 'EV-02', name: 'Beta Electric Van', capacity: 65, battery_range_km: 95.0, energy_rate_kwh_per_km: 0.22 }
      ],
      methods_summary: {
        greedy: {
          method: 'greedy',
          method_name: 'Method A — Conventional Greedy Baseline',
          trial_count: 3,
          feasibility_percentage: 100.0,
          best_objective: 25.25,
          mean_objective: 25.25,
          std_objective: 0.0,
          mean_distance_km: 25.25,
          mean_travel_time_min: 37.9,
          median_runtime_ms: 0.05,
          p95_runtime_ms: 0.05,
          mean_violations: 0.0,
          best_solution_routes: [
            {
              vehicle_id: 'EV-01',
              vehicle_name: 'Alpha Electric Van',
              stop_sequence: [
                { type: 'depot', id: 'depot-central', name: 'Central Hub', latitude: 13.0827, longitude: 80.2707 },
                { type: 'waypoint', id: 'wp-1', name: 'T. Nagar Hub', latitude: 13.0418, longitude: 80.2341 },
                { type: 'depot', id: 'depot-central', name: 'Central Hub', latitude: 13.0827, longitude: 80.2707 }
              ],
              total_distance_km: 25.25,
              total_energy_kwh: 5.55,
              total_demand_delivered: 45,
              capacity_utilized_percent: 69.2,
              feasible: true
            }
          ]
        },
        classical_sa: {
          method: 'classical_sa',
          method_name: 'Method B — Classical Simulated Annealing',
          trial_count: 3,
          feasibility_percentage: 100.0,
          best_objective: 25.25,
          mean_objective: 25.25,
          std_objective: 0.0,
          mean_distance_km: 25.25,
          mean_travel_time_min: 37.9,
          median_runtime_ms: 1.25,
          p95_runtime_ms: 1.30,
          mean_violations: 0.0,
          best_solution_routes: []
        },
        qubo_sa: {
          method: 'qubo_sa',
          method_name: 'Method C — QUBO + Simulated Annealing Solver',
          trial_count: 3,
          feasibility_percentage: 100.0,
          best_objective: 25.25,
          mean_objective: 25.25,
          std_objective: 0.0,
          mean_distance_km: 25.25,
          mean_travel_time_min: 37.9,
          median_runtime_ms: 0.45,
          p95_runtime_ms: 0.48,
          mean_violations: 0.0,
          best_solution_routes: [
            {
              vehicle_id: 'EV-01',
              vehicle_name: 'Alpha Electric Van',
              stop_sequence: [
                { type: 'depot', id: 'depot-central', name: 'Central Hub', latitude: 13.0827, longitude: 80.2707 },
                { type: 'waypoint', id: 'wp-1', name: 'T. Nagar Hub', latitude: 13.0418, longitude: 80.2341 },
                { type: 'depot', id: 'depot-central', name: 'Central Hub', latitude: 13.0827, longitude: 80.2707 }
              ],
              total_distance_km: 25.25,
              total_energy_kwh: 5.55,
              total_demand_delivered: 45,
              capacity_utilized_percent: 69.2,
              feasible: true
            }
          ],
          convergence_history: [
            { iteration: 0, temperature: 100.0, current_energy: 45.0, best_energy: 45.0 },
            { iteration: 500, temperature: 10.0, current_energy: 25.25, best_energy: 25.25 }
          ]
        }
      },
      trials: [],
      brute_force_exact: {
        method: 'brute_force_exact',
        method_name: 'Mathematical Ground-Truth (Exhaustive Brute-Force)',
        num_evaluated_states: 4096,
        min_qubo_energy: 25.25,
        best_bitstring: '000010011000',
        total_distance_km: 25.25,
        constraint_violations: 0,
        all_feasible: true,
        routes: [],
        execution_time_ms: 15.0
      },
      created_at: new Date().toISOString()
    });

    render(<QuboRoutingPage />);

    await waitFor(() => {
      expect(screen.getByText(/No historical experiments found/i)).toBeInTheDocument();
    });

    const runBtn = screen.getByRole('button', { name: /Run Optimization/i });
    fireEvent.click(runBtn);

    await waitFor(
      () => {
        expect(api.runOptimization).toHaveBeenCalled();
        expect(screen.getByText(/Methodological Benchmark Comparison/i)).toBeInTheDocument();
        expect(screen.getAllByText(/Method A — Conventional Greedy Baseline/i).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/Method B — Classical Simulated Annealing/i).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/Method C — QUBO \+ Simulated Annealing Solver/i).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/Exact Oracle \(Exhaustive Brute-Force\)/i).length).toBeGreaterThan(0);
        expect(screen.getByText(/Chennai Fleet Routing Geometry/i)).toBeInTheDocument();
      },
      { timeout: 4000 }
    );
  });
});
