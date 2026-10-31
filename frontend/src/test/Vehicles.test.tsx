import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { VehiclesPage } from '../pages/VehiclesPage';
import { VehicleDetailPage } from '../pages/VehicleDetailPage';
import { api } from '../services/api';

vi.mock('../services/api', () => ({
  api: {
    getVehicles: vi.fn(),
    getVehicle: vi.fn(),
    getVehicleTelemetry: vi.fn(),
    createVehicle: vi.fn(),
    updateVehicle: vi.fn(),
    deleteVehicle: vi.fn(),
  },
}));

vi.mock('../components/SimulatedMap', () => ({
  SimulatedMap: () => <div data-testid="simulated-map-mock">Simulated Map Mock</div>,
}));

describe('VehiclesPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', async () => {
    (api.getVehicles as any).mockReturnValue(new Promise(() => {})); // pending

    render(<VehiclesPage onViewVehicle={vi.fn()} />);
    expect(screen.getByText(/loading fleet records/i)).toBeInTheDocument();
  });

  it('renders empty state when no vehicles returned', async () => {
    (api.getVehicles as any).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      limit: 10,
      total_pages: 1,
    });

    render(<VehiclesPage onViewVehicle={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/no vehicles found/i)).toBeInTheDocument();
    });
  });

  it('renders error state on API failure', async () => {
    (api.getVehicles as any).mockRejectedValue(new Error('Network error loading fleet'));

    render(<VehiclesPage onViewVehicle={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/network error loading fleet/i)).toBeInTheDocument();
    });
  });

  it('renders vehicle list items when populated', async () => {
    (api.getVehicles as any).mockResolvedValue({
      items: [
        {
          id: 1,
          vehicle_identifier: 'SIM-DEMO-001',
          name: 'Metro Transit Shuttle A1',
          status: 'moving',
          created_at: '2026-10-29T00:00:00Z',
          updated_at: '2026-10-29T00:00:00Z',
          latest_telemetry: {
            id: 101,
            vehicle_id: 1,
            timestamp: '2026-10-29T00:00:00Z',
            latitude: 13.0827,
            longitude: 80.2707,
            speed: 48.5,
            status: 'moving',
            battery_level: 84.0,
          },
        },
      ],
      total: 1,
      page: 1,
      limit: 10,
      total_pages: 1,
    });

    render(<VehiclesPage onViewVehicle={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('SIM-DEMO-001')).toBeInTheDocument();
      expect(screen.getByText('Metro Transit Shuttle A1')).toBeInTheDocument();
      expect(screen.getByText('48.5 km/h')).toBeInTheDocument();
    });
  });

  it('renders VehicleDetailPage with map and telemetry', async () => {
    (api.getVehicle as any).mockResolvedValue({
      id: 1,
      vehicle_identifier: 'SIM-DEMO-001',
      name: 'Metro Transit Shuttle A1',
      status: 'moving',
      created_at: '2026-10-29T00:00:00Z',
      updated_at: '2026-10-29T00:00:00Z',
      latest_telemetry: {
        id: 101,
        vehicle_id: 1,
        timestamp: '2026-10-29T00:00:00Z',
        latitude: 13.0827,
        longitude: 80.2707,
        speed: 48.5,
        status: 'moving',
        battery_level: 84.0,
      },
      telemetry_history_sample: [],
      total_telemetry_records: 1,
    });
    (api.getVehicleTelemetry as any).mockResolvedValue({
      items: [
        {
          id: 101,
          vehicle_id: 1,
          timestamp: '2026-10-29T00:00:00Z',
          latitude: 13.0827,
          longitude: 80.2707,
          speed: 48.5,
          status: 'moving',
          battery_level: 84.0,
        },
      ],
      total: 1,
      page: 1,
      limit: 30,
      total_pages: 1,
    });

    render(<VehicleDetailPage vehicleId={1} onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Metro Transit Shuttle A1')).toBeInTheDocument();
      expect(screen.getByText(/SIM-DEMO-001/)).toBeInTheDocument();
    });
  });
});
