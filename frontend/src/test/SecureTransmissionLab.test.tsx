import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { SecureTransmissionLabPage } from '../pages/SecureTransmissionLabPage';
import { api } from '../services/api';

vi.mock('../services/api', () => ({
  api: {
    getTransmissionAnalytics: vi.fn(),
    getTransmissionExperiments: vi.fn(),
    runSecurityDemonstration: vi.fn(),
    runTransmissionExperiment: vi.fn(),
  },
}));

describe('SecureTransmissionLabPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.getTransmissionAnalytics as any).mockResolvedValue({
      total_transmissions: 60,
      plaintext_transmissions: 27,
      protected_transmissions: 33,
      successful_transmissions: 56,
      rejected_transmissions: 4,
      overall_success_rate: 93.33,
      tampering_detected_count: 2,
      replay_detected_count: 1,
      unauthorized_identity_count: 1,
      median_plaintext_latency_ms: 6.5,
      median_protected_latency_ms: 88.0,
      median_encryption_latency_ms: 45.0,
      median_decryption_latency_ms: 43.0,
      mean_payload_expansion_bytes: 1055.6,
      mean_payload_expansion_percent: 389.45,
      by_payload_category: {
        small: { count: 6, mean_original_bytes: 200, mean_envelope_bytes: 1200, mean_expansion_pct: 500 },
        medium: { count: 21, mean_original_bytes: 250, mean_envelope_bytes: 1300, mean_expansion_pct: 420 },
        large: { count: 6, mean_original_bytes: 600, mean_envelope_bytes: 1750, mean_expansion_pct: 190 }
      }
    });
    (api.getTransmissionExperiments as any).mockResolvedValue({
      items: [
        {
          transmission_id: 'TX-IBE-DEMO001',
          vehicle_identifier: 'SIM-VEH-001',
          sender_identity: 'SIM-VEH-001@fleet.iot.local',
          recipient_identity: 'fleet-management-server-core',
          transmission_mode: 'ibe_protected',
          payload_category: 'medium',
          original_payload_size_bytes: 250,
          encrypted_envelope_size_bytes: 1250,
          payload_expansion_bytes: 1000,
          payload_expansion_percent: 400.0,
          encryption_duration_ms: 45.2,
          decryption_duration_ms: 42.8,
          server_processing_duration_ms: 50.0,
          total_duration_ms: 95.2,
          status: 'success',
          tampered_flag: false,
          replayed_flag: false,
          unauthorized_identity_flag: false,
          created_at: new Date().toISOString(),
          telemetry_persisted: true
        }
      ],
      total: 1,
      page: 1,
      limit: 15,
      total_pages: 1
    });
  });

  it('renders Secure Transmission Lab titles and attack demo options', async () => {
    render(<SecureTransmissionLabPage />);

    expect(screen.getByText(/secure vehicle-to-server transmission lab/i)).toBeInTheDocument();
    expect(screen.getByText(/controlled security demonstration & attack verification/i)).toBeInTheDocument();
    expect(screen.getByText(/1\. Authorized Transmission/i)).toBeInTheDocument();
    expect(screen.getByText(/2\. Rogue \/ Unenrolled Identity/i)).toBeInTheDocument();
    expect(screen.getByText(/3\. Tampered Ciphertext Body/i)).toBeInTheDocument();
    expect(screen.getByText(/4\. Tampered Authentication Tag/i)).toBeInTheDocument();
    expect(screen.getByText(/5\. Replay Attack Resubmission/i)).toBeInTheDocument();
    expect(screen.getByText(/6\. Cross-Vehicle Substitution/i)).toBeInTheDocument();
  });

  it('displays real transmission records and metrics from API', async () => {
    render(<SecureTransmissionLabPage />);

    await waitFor(() => {
      expect(screen.getByText('TX-IBE-DEMO001')).toBeInTheDocument();
      expect(screen.getByText('SIM-VEH-001')).toBeInTheDocument();
    });
  });
});
