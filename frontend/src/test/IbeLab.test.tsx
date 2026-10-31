import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { IbeLabPage } from '../pages/IbeLabPage';
import { api } from '../services/api';

vi.mock('../services/api', () => ({
  api: {
    getIBEStatus: vi.fn(),
    getVehicles: vi.fn(),
    getIBEExperiments: vi.fn(),
    encryptIBE: vi.fn(),
    decryptIBE: vi.fn(),
    createIBEExperiment: vi.fn(),
  },
}));

describe('IbeLabPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.getIBEStatus as any).mockResolvedValue({
      status: 'ready',
      scheme: 'Boneh-Franklin-BN128-AES256GCM',
      curve: 'BN128 (alt_bn128)',
      pairing_type: 'Asymmetric Optimal Ate (Type 3)',
      symmetric_cipher: 'AES-256-GCM',
      key_derivation: 'HKDF-SHA256',
      public_params_available: true,
      pkg_trust_model: 'Centralized PKG with key escrow limitation.',
      is_simulated_iot_layer: true,
    });
    (api.getVehicles as any).mockResolvedValue({ items: [], total: 0 });
    (api.getIBEExperiments as any).mockResolvedValue({ items: [], total: 0 });
  });

  it('renders IBE Lab titles and cryptographic trust model notes', async () => {
    render(<IbeLabPage />);

    expect(screen.getByText(/identity-based encryption \(ibe\) lab/i)).toBeInTheDocument();
    expect(screen.getByText(/key-escrow limitation/i)).toBeInTheDocument();
    expect(screen.getAllByText(/boneh-franklin/i).length).toBeGreaterThan(0);
  });

  it('handles encrypt action and displays ciphertext preview', async () => {
    (api.encryptIBE as any).mockResolvedValue({
      version: '1.0',
      scheme: 'Boneh-Franklin-BN128-AES256GCM',
      recipient_identity: 'traffic-control-hub-01',
      u_point: { x: [1, 2], y: [3, 4] },
      salt_b64: 'c2FsdDEyMw==',
      nonce_b64: 'bm9uY2UxMjM0NTY3',
      ciphertext_b64: 'Y2lwaGVydGV4dF9kYXRhX2Jhc2U2NA==',
      payload_size_bytes: 120,
      ciphertext_size_bytes: 136,
      encryption_duration_ms: 82.5,
    });

    render(<IbeLabPage />);

    const encryptBtn = screen.getByRole('button', { name: /encrypt only/i });
    fireEvent.click(encryptBtn);

    await waitFor(() => {
      expect(api.encryptIBE).toHaveBeenCalledWith(
        'traffic-control-hub-01',
        expect.any(String)
      );
      expect(screen.getByText(/Y2lwaGVydGV4dF9kYXRhX2Jhc2U2NA==/)).toBeInTheDocument();
    });
  });

  it('renders authorized decryption outcome when triggered', async () => {
    (api.encryptIBE as any).mockResolvedValue({
      version: '1.0',
      scheme: 'Boneh-Franklin-BN128-AES256GCM',
      recipient_identity: 'traffic-control-hub-01',
      u_point: { x: [1, 2], y: [3, 4] },
      salt_b64: 'c2FsdDEyMw==',
      nonce_b64: 'bm9uY2UxMjM0NTY3',
      ciphertext_b64: 'dGVzdF9jdA==',
      payload_size_bytes: 50,
      ciphertext_size_bytes: 66,
      encryption_duration_ms: 70.0,
    });

    (api.decryptIBE as any).mockResolvedValue({
      success: true,
      decrypted_payload: '{"vehicle": 1}',
      error: null,
      decryption_duration_ms: 65.2,
    });

    render(<IbeLabPage />);

    // First encrypt to produce bundle
    fireEvent.click(screen.getByRole('button', { name: /encrypt only/i }));

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /authorized decrypt/i }).length).toBeGreaterThan(0);
    });

    // Then decrypt
    fireEvent.click(screen.getAllByRole('button', { name: /authorized decrypt/i })[0]);

    await waitFor(() => {
      expect(screen.getByText(/VERIFIED MATCH/i)).toBeInTheDocument();
      expect(screen.getByText(/65\.2 ms/)).toBeInTheDocument();
    });
  });
});
