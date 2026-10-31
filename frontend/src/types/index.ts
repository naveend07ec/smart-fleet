export interface Telemetry {
  id: number;
  vehicle_id: number;
  timestamp: string;
  latitude: number;
  longitude: number;
  speed: number;
  status: 'moving' | 'idle' | 'offline';
  battery_level: number;
}

export interface Vehicle {
  id: number;
  vehicle_identifier: string;
  name: string;
  status: 'moving' | 'idle' | 'offline';
  created_at: string;
  updated_at: string;
  latest_telemetry?: Telemetry | null;
}

export interface VehicleDetail extends Vehicle {
  telemetry_history_sample: Telemetry[];
  total_telemetry_records: number;
}

export interface VehiclePagination {
  items: Vehicle[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface TelemetryPagination {
  items: Telemetry[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface DashboardSummary {
  total_vehicles: number;
  status_breakdown: {
    moving: number;
    idle: number;
    offline: number;
  };
  speed_stats: {
    average_speed_active_kmh: number;
    max_speed_kmh: number;
  };
  latest_telemetry_at: string | null;
  recent_trend: {
    time_label: string;
    record_count: number;
    avg_speed: number;
  }[];
  is_simulated: boolean;
  disclaimer: string;
}

export interface AnalyticsOverview {
  total_records: number;
  status_distribution: {
    status: string;
    count: number;
    percentage: number;
  }[];
  speed_analytics: {
    overall_average_kmh: number;
    active_average_kmh: number;
    max_recorded_kmh: number;
  };
  activity_over_time: {
    timestamp_bucket: string;
    moving_count: number;
    idle_count: number;
    offline_count: number;
  }[];
  telemetry_volume_over_time: {
    timestamp_bucket: string;
    record_count: number;
  }[];
  top_active_vehicles: {
    vehicle_id: number;
    vehicle_identifier: string;
    name: string;
    total_telemetry_points: number;
    average_speed: number;
    max_speed: number;
    latest_battery_level: number;
  }[];
  is_simulated: boolean;
  disclaimer: string;
}

export interface SimulationStatus {
  is_running: boolean;
  vehicle_count: number;
  interval_seconds: number;
  tick_count: number;
  random_seed?: number | null;
  started_at?: string | null;
  last_tick_at?: string | null;
  message: string;
  is_simulated: boolean;
}

export interface SimulationStartParams {
  vehicle_count: number;
  interval_seconds: number;
  random_seed?: number;
}

export interface VehicleCreatePayload {
  vehicle_identifier: string;
  name: string;
  status: 'moving' | 'idle' | 'offline';
}

export interface VehicleUpdatePayload {
  name?: string;
  status?: 'moving' | 'idle' | 'offline';
}

export interface IBEStatus {
  status: string;
  scheme: string;
  curve: string;
  pairing_type: string;
  symmetric_cipher: string;
  key_derivation: string;
  public_params_available: boolean;
  pkg_trust_model: string;
  is_simulated_iot_layer: boolean;
}

export interface IBECiphertextBundle {
  version: string;
  scheme: string;
  recipient_identity: string;
  u_point: {
    x: number[];
    y: number[];
  };
  salt_b64: string;
  nonce_b64: string;
  ciphertext_b64: string;
  payload_size_bytes: number;
  ciphertext_size_bytes: number;
  encryption_duration_ms: number;
}

export interface IBEDecryptResult {
  success: boolean;
  decrypted_payload: string | null;
  error: string | null;
  decryption_duration_ms: number;
}

export interface IBEExperiment {
  id: number;
  experiment_id: string;
  timestamp: string;
  scheme: string;
  recipient_identity: string;
  unauthorized_identity?: string | null;
  payload_size_bytes: number;
  ciphertext_size_bytes: number;
  encryption_duration_ms: number;
  decryption_duration_ms: number;
  authorized_success: boolean;
  unauthorized_rejected: boolean;
  tamper_check_passed: boolean;
  status: string;
  notes?: string | null;
}

export interface IBEExperimentList {
  items: IBEExperiment[];
  total: number;
}

export interface IBEExperimentCreatePayload {
  recipient_identity: string;
  unauthorized_identity: string;
  payload: string;
  notes?: string;
}

// ==========================================
// Phase 3 — Secure Vehicle-to-Server Types
// ==========================================

export interface VehicleEnrollment {
  id: number;
  vehicle_identifier: string;
  assigned_identity: string;
  is_enrolled: boolean;
  enrolled_at: string;
  revoked_at?: string | null;
  signing_public_key?: string | null;
  notes?: string | null;
}

export interface SecureTransmission {
  transmission_id: string;
  batch_id?: string | null;
  vehicle_identifier: string;
  sender_identity: string;
  recipient_identity: string;
  transmission_mode: 'plaintext' | 'ibe_protected';
  payload_category: 'small' | 'medium' | 'large';
  original_payload_size_bytes: number;
  encrypted_envelope_size_bytes: number;
  payload_expansion_bytes: number;
  payload_expansion_percent: number;
  encryption_duration_ms: number;
  decryption_duration_ms: number;
  server_processing_duration_ms: number;
  total_duration_ms: number;
  status: 'success' | 'rejected' | 'failed';
  rejection_reason?: string | null;
  tampered_flag: boolean;
  replayed_flag: boolean;
  unauthorized_identity_flag: boolean;
  signature_b64?: string | null;
  signature_verified?: boolean;
  message_id?: string | null;
  created_at: string;
  telemetry_persisted: boolean;
}

export interface SecureTransmissionList {
  items: SecureTransmission[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface ExperimentRunPayload {
  vehicle_count: number;
  messages_per_vehicle: number;
  mode: 'plaintext' | 'ibe_protected' | 'both';
  payload_category: 'small' | 'medium' | 'large';
  notes?: string;
}

export interface ExperimentRunResult {
  batch_id: string;
  total_attempted: number;
  total_successful: number;
  total_rejected: number;
  success_rate_percent: number;
  plaintext_count: number;
  protected_count: number;
  metrics: {
    mode_evaluated: string;
    payload_category: string;
    vehicle_count: number;
    messages_per_vehicle: number;
    baseline_plaintext: {
      count: number;
      median_duration_ms: number;
      mean_duration_ms: number;
      mean_payload_bytes: number;
    };
    ibe_protected: {
      count: number;
      median_total_duration_ms: number;
      mean_total_duration_ms: number;
      median_encryption_ms: number;
      mean_encryption_ms: number;
      median_decryption_ms: number;
      mean_decryption_ms: number;
      mean_envelope_bytes: number;
      mean_payload_expansion_percent: number;
    };
  };
  records: SecureTransmission[];
}

export interface TransmissionAnalytics {
  total_transmissions: number;
  plaintext_transmissions: number;
  protected_transmissions: number;
  successful_transmissions: number;
  rejected_transmissions: number;
  overall_success_rate: number;
  tampering_detected_count: number;
  replay_detected_count: number;
  unauthorized_identity_count: number;
  median_plaintext_latency_ms: number;
  median_protected_latency_ms: number;
  median_encryption_latency_ms: number;
  median_decryption_latency_ms: number;
  mean_payload_expansion_bytes: number;
  mean_payload_expansion_percent: number;
  by_payload_category: Record<string, {
    count: number;
    mean_original_bytes: number;
    mean_envelope_bytes: number;
    mean_expansion_pct: number;
  }>;
}

export interface SecurityDemonstrationPayload {
  scenario: 'valid_authorized' | 'unauthorized_identity' | 'tampered_ciphertext' | 'tampered_tag' | 'replay_attack' | 'cross_vehicle_substitution';
  vehicle_identifier?: string;
}

// ==========================================
// Phase 4: Blind Quantum Computing (BQC)
// ==========================================

export interface BqcStatus {
  status: string;
  protocol: string;
  quantum_simulator: string;
  max_qubits_supported: number;
  client_model: string;
  server_model: string;
  cluster_topologies: Record<string, string>;
  research_disclaimer: string;
}

export interface BqcDemonstrationResult {
  num_candidates: number;
  candidate_names: string[];
  mode_a: {
    mode: string;
    num_candidates: number;
    selected_depot_index: number;
    selected_depot_name: string;
    selected_cost: number;
    all_costs: number[];
    execution_time_ms: number;
    wire_bytes: number;
    server_visibility: string;
    privacy_guarantee: string;
    server_learned_gps: boolean;
    server_learned_costs: boolean;
    server_learned_output: boolean;
  };
  mode_b: {
    mode: string;
    num_candidates: number;
    num_qubits: number;
    cluster_topology: string;
    graph_edges: [number, number][];
    selected_depot_index: number;
    selected_depot_name: string;
    selected_cost: number;
    all_costs: number[];
    classical_min_index: number;
    correctness: boolean;
    client_prep_ms: number;
    server_quantum_ms: number;
    total_execution_ms: number;
    client_to_server_bytes: number;
    server_to_client_bytes: number;
    total_wire_bytes: number;
    blinded_angles_rad: number[];
    server_raw_outcomes: number[];
    client_unpadded_outcomes: number[];
    angle_entropy_bits: number;
    max_theoretical_entropy: number;
    server_visibility: string;
    privacy_guarantee: string;
    server_learned_gps: boolean;
    server_learned_costs: boolean;
    server_learned_output: boolean;
    diagnostics: Record<string, any>;
    server_visibility_audit: {
      server_received_qubits: number;
      server_received_angles_count: number;
      server_observed_angles_sample: number[];
      server_observed_raw_outcomes: number[];
      server_learned_gps: boolean;
      server_learned_costs: boolean;
      server_learned_target_depot: boolean;
      total_bytes_received: number;
      total_bytes_sent: number;
    };
  };
  correctness_verified: boolean;
  wire_expansion_percent: number;
  privacy_contrast: Record<string, string>;
}

export interface BqcBatchSummary {
  experiment_id: number;
  num_candidates: number;
  trials_executed_per_mode: number;
  mode_a: {
    median_latency_ms: number;
    mean_latency_ms: number;
    p95_latency_ms: number;
    min_latency_ms: number;
    max_latency_ms: number;
    mean_wire_bytes: number;
  };
  mode_b: {
    median_latency_ms: number;
    mean_latency_ms: number;
    p95_latency_ms: number;
    min_latency_ms: number;
    max_latency_ms: number;
    mean_wire_bytes: number;
  };
  wire_expansion_percent: number;
  algorithmic_correctness_rate: number;
  universal_blindness_verified_rate: number;
  mean_angle_entropy_bits: number;
  total_variation_distance: number;
  distinguishability_verdict: string;
}

export interface BqcExperimentItem {
  id: number;
  name: string;
  num_candidates: number;
  num_qubits: number;
  cluster_topology: string;
  created_at: string;
  total_trials: number;
  correctness_rate: number;
}

// ---------------------------------------------------------------------------
// Phase 5: QUBO / Simulated Annealing Fleet Routing Types
// ---------------------------------------------------------------------------

export interface RoutingWaypoint {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  demand: number;
  priority: number;
}

export interface RoutingDepot {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
}

export interface RoutingVehicleConfig {
  id: string;
  name: string;
  capacity: number;
  battery_range_km: number;
  energy_rate_kwh_per_km: number;
}

export interface RoutingStopItem {
  type: 'depot' | 'waypoint';
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  demand?: number;
  priority?: number;
}

export interface VehicleRouteResult {
  vehicle_id: string;
  vehicle_name: string;
  stop_sequence: RoutingStopItem[];
  total_distance_km: number;
  total_energy_kwh: number;
  total_demand_delivered: number;
  capacity_utilized_percent: number;
  feasible: boolean;
}

export interface MethodRoutingResult {
  method_name: string;
  routes: VehicleRouteResult[];
  total_distance_km: number;
  total_energy_kwh: number;
  execution_time_ms: number;
  max_route_distance_km: number;
  route_variance_km: number;
  all_feasible: boolean;
  qubo_energy_score?: number;
}

export interface ConvergenceStep {
  iteration: number;
  temperature: number;
  current_energy: number;
  best_energy: number;
}

export interface RoutingOptimizationResponse {
  scenario: string;
  num_vehicles: number;
  num_waypoints: number;
  depot: RoutingDepot;
  classical_heuristic: MethodRoutingResult;
  qubo_simulated_annealing: MethodRoutingResult;
  differential_kpis: {
    distance_saved_km: number;
    distance_reduction_percent: number;
    energy_saved_kwh: number;
    energy_savings_percent: number;
    load_balance_improvement: string;
    classical_time_ms: number;
    qubo_time_ms: number;
    valid_solution: boolean;
  };
  convergence_history: ConvergenceStep[];
  experiment_id?: number | null;
  created_at: string;
}

export interface RoutingDefaultsResponse {
  depot: RoutingDepot;
  waypoints: RoutingWaypoint[];
  vehicles: RoutingVehicleConfig[];
  scenarios: {
    id: string;
    name: string;
    description: string;
  }[];
}

export interface RoutingExperimentListItem {
  id: number;
  name: string;
  scenario: string;
  num_vehicles: number;
  num_waypoints: number;
  classical_distance_km: number;
  qubo_distance_km: number;
  distance_reduction_percent: number;
  energy_savings_percent: number;
  created_at: string;
}

// ==========================================
// Phase 5 Dedicated Fleet Optimization Types
// ==========================================

export interface OptimizationScenarioInfo {
  id: string;
  name: string;
  description: string;
  vehicle_count: number;
  destination_count: number;
  max_steps: number;
  num_qubo_variables: number;
  state_space_size: string;
  depot: RoutingDepot;
  vehicles: RoutingVehicleConfig[];
  destinations: RoutingWaypoint[];
}

export interface MethodComparisonSummary {
  method: string;
  method_name: string;
  trial_count: number;
  feasibility_percentage: number;
  best_objective: number;
  mean_objective: number;
  std_objective: number;
  mean_distance_km: number;
  mean_travel_time_min: number;
  median_runtime_ms: number;
  p95_runtime_ms: number;
  mean_violations: number;
  best_solution_routes: VehicleRouteResult[];
  convergence_history?: ConvergenceStep[];
}

export interface OptimizationTrialDetail {
  trial_number: number;
  method: string;
  objective_value: number;
  total_distance: number;
  estimated_travel_time: number;
  execution_time_ms: number;
  feasibility_status: boolean;
  constraint_violations: number;
  solution_data: {
    routes: VehicleRouteResult[];
    total_energy_kwh?: number;
    route_variance_km?: number;
  };
}

export interface OptimizationRunResponse {
  experiment_id?: number | null;
  experiment_name?: string | null;
  scenario_name: string;
  vehicle_count: number;
  destination_count: number;
  method: string;
  random_seed: number;
  solver_parameters: Record<string, any>;
  depot: RoutingDepot;
  destinations: RoutingWaypoint[];
  vehicles: RoutingVehicleConfig[];
  methods_summary: Record<string, MethodComparisonSummary>;
  trials: OptimizationTrialDetail[];
  brute_force_exact?: {
    method: string;
    method_name: string;
    num_evaluated_states: number;
    min_qubo_energy: number;
    best_bitstring: string;
    total_distance_km: number;
    constraint_violations: number;
    all_feasible: boolean;
    routes: VehicleRouteResult[];
    execution_time_ms: number;
  } | null;
  created_at: string;
}

export interface OptimizationExperimentListItem {
  id: number;
  experiment_name: string;
  scenario_name: string;
  vehicle_count: number;
  destination_count: number;
  method: string;
  random_seed: number;
  objective_value?: number | null;
  total_distance?: number | null;
  execution_time_ms?: number | null;
  feasibility_status: boolean;
  constraint_violations: number;
  created_at: string;
}



