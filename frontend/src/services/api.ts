import {
  Vehicle,
  VehicleDetail,
  VehiclePagination,
  TelemetryPagination,
  DashboardSummary,
  AnalyticsOverview,
  SimulationStatus,
  SimulationStartParams,
  VehicleCreatePayload,
  VehicleUpdatePayload,
  IBEStatus,
  IBECiphertextBundle,
  IBEDecryptResult,
  IBEExperiment,
  IBEExperimentCreatePayload,
  IBEExperimentList
} from '../types';

const API_BASE = '/api';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = errJson.detail;
      } else if (errJson && errJson.message) {
        errorDetail = errJson.message;
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    return handleResponse<{ status: string; version: string; is_simulated_system: boolean }>(res);
  },

  async getDashboardSummary(): Promise<DashboardSummary> {
    const res = await fetch(`${API_BASE}/dashboard/summary`);
    return handleResponse<DashboardSummary>(res);
  },

  async getVehicles(
    page: number = 1,
    limit: number = 10,
    search?: string,
    status?: string
  ): Promise<VehiclePagination> {
    const params = new URLSearchParams({
      page: String(page),
      limit: String(limit),
    });
    if (search && search.trim()) params.append('search', search.trim());
    if (status && status !== 'all') params.append('status', status.trim());

    const res = await fetch(`${API_BASE}/vehicles?${params.toString()}`);
    return handleResponse<VehiclePagination>(res);
  },

  async getVehicle(id: string | number): Promise<VehicleDetail> {
    const res = await fetch(`${API_BASE}/vehicles/${id}`);
    return handleResponse<VehicleDetail>(res);
  },

  async createVehicle(payload: VehicleCreatePayload): Promise<Vehicle> {
    const res = await fetch(`${API_BASE}/vehicles`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<Vehicle>(res);
  },

  async updateVehicle(id: string | number, payload: VehicleUpdatePayload): Promise<Vehicle> {
    const res = await fetch(`${API_BASE}/vehicles/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<Vehicle>(res);
  },

  async deleteVehicle(id: string | number): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/vehicles/${id}`, {
      method: 'DELETE',
    });
    return handleResponse<{ status: string; message: string }>(res);
  },

  async getVehicleTelemetry(
    id: string | number,
    page: number = 1,
    limit: number = 25
  ): Promise<TelemetryPagination> {
    const res = await fetch(`${API_BASE}/vehicles/${id}/telemetry?page=${page}&limit=${limit}`);
    return handleResponse<TelemetryPagination>(res);
  },

  async getAnalyticsOverview(): Promise<AnalyticsOverview> {
    const res = await fetch(`${API_BASE}/analytics/overview`);
    return handleResponse<AnalyticsOverview>(res);
  },

  async getSimulationStatus(): Promise<SimulationStatus> {
    const res = await fetch(`${API_BASE}/simulation/status`);
    return handleResponse<SimulationStatus>(res);
  },

  async startSimulation(params: SimulationStartParams): Promise<SimulationStatus> {
    const res = await fetch(`${API_BASE}/simulation/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    return handleResponse<SimulationStatus>(res);
  },

  async stopSimulation(): Promise<SimulationStatus> {
    const res = await fetch(`${API_BASE}/simulation/stop`, {
      method: 'POST',
    });
    return handleResponse<SimulationStatus>(res);
  },

  async getIBEStatus(): Promise<IBEStatus> {
    const res = await fetch(`${API_BASE}/security/ibe/status`);
    return handleResponse<IBEStatus>(res);
  },

  async setupIBE(forceReinit: boolean = false): Promise<any> {
    const res = await fetch(`${API_BASE}/security/ibe/setup?force_reinit=${forceReinit}`, {
      method: 'POST',
    });
    return handleResponse<any>(res);
  },

  async encryptIBE(recipientIdentity: string, payload: string): Promise<IBECiphertextBundle> {
    const res = await fetch(`${API_BASE}/security/ibe/encrypt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        recipient_identity: recipientIdentity,
        payload: payload,
      }),
    });
    return handleResponse<IBECiphertextBundle>(res);
  },

  async decryptIBE(recipientIdentity: string, ciphertextBundle: any): Promise<IBEDecryptResult> {
    const res = await fetch(`${API_BASE}/security/ibe/decrypt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        recipient_identity: recipientIdentity,
        ciphertext_bundle: ciphertextBundle,
      }),
    });
    return handleResponse<IBEDecryptResult>(res);
  },

  async createIBEExperiment(payload: IBEExperimentCreatePayload): Promise<IBEExperiment> {
    const res = await fetch(`${API_BASE}/security/ibe/experiments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<IBEExperiment>(res);
  },

  async getIBEExperiments(page: number = 1, limit: number = 20): Promise<IBEExperimentList> {
    const res = await fetch(`${API_BASE}/security/ibe/experiments?page=${page}&limit=${limit}`);
    return handleResponse<IBEExperimentList>(res);
  },

  async getIBEExperiment(experimentId: string): Promise<IBEExperiment> {
    const res = await fetch(`${API_BASE}/security/ibe/experiments/${experimentId}`);
    return handleResponse<IBEExperiment>(res);
  },

  // ==========================================
  // Phase 3: Secure Transmission Endpoints
  // ==========================================

  async getVehicleEnrollments(): Promise<any[]> {
    const res = await fetch(`${API_BASE}/secure-transmission/enrollments`);
    return handleResponse<any[]>(res);
  },

  async enrollVehicle(vehicleIdentifier: string, assignedIdentity?: string, notes?: string): Promise<any> {
    const res = await fetch(`${API_BASE}/secure-transmission/enroll`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vehicle_identifier: vehicleIdentifier,
        assigned_identity: assignedIdentity,
        notes: notes,
      }),
    });
    return handleResponse<any>(res);
  },

  async runSecurityDemonstration(scenario: string, vehicleIdentifier?: string): Promise<any> {
    const res = await fetch(`${API_BASE}/secure-transmission/demonstration`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scenario,
        vehicle_identifier: vehicleIdentifier,
      }),
    });
    return handleResponse<any>(res);
  },

  async runTransmissionExperiment(payload: any): Promise<any> {
    const res = await fetch(`${API_BASE}/secure-transmission/experiments/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<any>(res);
  },

  async getTransmissionExperiments(
    page: number = 1,
    limit: number = 25,
    mode?: string,
    statusFilter?: string,
    batchId?: string
  ): Promise<any> {
    const params = new URLSearchParams({
      page: String(page),
      limit: String(limit),
    });
    if (mode && mode !== 'all') params.append('mode', mode);
    if (statusFilter && statusFilter !== 'all') params.append('status_filter', statusFilter);
    if (batchId && batchId.trim()) params.append('batch_id', batchId.trim());

    const res = await fetch(`${API_BASE}/secure-transmission/experiments?${params.toString()}`);
    return handleResponse<any>(res);
  },

  async getTransmissionDetail(transmissionId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/secure-transmission/experiments/${transmissionId}`);
    return handleResponse<any>(res);
  },

  async getTransmissionAnalytics(): Promise<any> {
    const res = await fetch(`${API_BASE}/secure-transmission/analytics`);
    return handleResponse<any>(res);
  },

  async getSecurityEvents(limit: number = 50): Promise<any[]> {
    const res = await fetch(`${API_BASE}/secure-transmission/security-events?limit=${limit}`);
    return handleResponse<any[]>(res);
  },

  // Phase 4: Blind Quantum Computing (BQC)
  async getBqcStatus(): Promise<any> {
    const res = await fetch(`${API_BASE}/security/bqc/status`);
    return handleResponse<any>(res);
  },

  async demonstrateBqc(payload: { num_candidates: number; cluster_topology?: string; vehicle_id?: number }): Promise<any> {
    const res = await fetch(`${API_BASE}/security/bqc/demonstrate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<any>(res);
  },

  async runBqcBatchTrials(payload: { num_candidates: number; trials_per_mode: number; cluster_topology?: string }): Promise<any> {
    const res = await fetch(`${API_BASE}/security/bqc/batch-trials`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<any>(res);
  },

  async getBqcExperiments(limit: number = 20): Promise<any[]> {
    const res = await fetch(`${API_BASE}/security/bqc/experiments?limit=${limit}`);
    return handleResponse<any[]>(res);
  },

  // ==========================================
  // Phase 5: QUBO / Simulated Annealing Routing (Legacy & New Endpoints)
  // ==========================================

  async getRoutingDefaults(): Promise<any> {
    const res = await fetch(`${API_BASE}/routing/defaults`);
    return handleResponse<any>(res);
  },

  async optimizeRoutes(payload: any): Promise<any> {
    const res = await fetch(`${API_BASE}/routing/optimize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<any>(res);
  },

  async getRoutingExperiments(limit: number = 20): Promise<any[]> {
    const res = await fetch(`${API_BASE}/routing/experiments?limit=${limit}`);
    return handleResponse<any[]>(res);
  },

  async getRoutingExperimentDetail(id: number): Promise<any> {
    const res = await fetch(`${API_BASE}/routing/experiments/${id}`);
    return handleResponse<any>(res);
  },

  async deleteRoutingExperiment(id: number): Promise<void> {
    const res = await fetch(`${API_BASE}/routing/experiments/${id}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      throw new Error(`Failed to delete routing experiment: ${res.statusText}`);
    }
  },

  // Dedicated Phase 5 Optimization Endpoints
  async getOptimizationStatus(): Promise<any> {
    const res = await fetch(`${API_BASE}/optimization/status`);
    return handleResponse<any>(res);
  },

  async getOptimizationScenarios(): Promise<any[]> {
    const res = await fetch(`${API_BASE}/optimization/scenarios`);
    return handleResponse<any[]>(res);
  },

  async runOptimization(payload: any): Promise<any> {
    const res = await fetch(`${API_BASE}/optimization/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<any>(res);
  },

  async getOptimizationExperiments(limit: number = 30): Promise<any[]> {
    const res = await fetch(`${API_BASE}/optimization/experiments?limit=${limit}`);
    return handleResponse<any[]>(res);
  },

  async getOptimizationExperimentDetail(id: number): Promise<any> {
    const res = await fetch(`${API_BASE}/optimization/experiments/${id}`);
    return handleResponse<any>(res);
  },

  async deleteOptimizationExperiment(id: number): Promise<void> {
    const res = await fetch(`${API_BASE}/optimization/experiments/${id}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      throw new Error(`Failed to delete optimization experiment: ${res.statusText}`);
    }
  },

  async getOptimizationAnalytics(): Promise<any> {
    const res = await fetch(`${API_BASE}/optimization/analytics`);
    return handleResponse<any>(res);
  },

  async compareOptimizationExperiments(ids: number[]): Promise<any[]> {
    const res = await fetch(`${API_BASE}/optimization/compare?experiment_ids=${ids.join(',')}`);
    return handleResponse<any[]>(res);
  },
};


