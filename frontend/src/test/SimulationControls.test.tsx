import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SimulationControls } from '../components/SimulationControls';
import { SimulationStatus } from '../types';

describe('SimulationControls Component', () => {
  const stoppedStatus: SimulationStatus = {
    is_running: false,
    vehicle_count: 25,
    interval_seconds: 3.0,
    tick_count: 0,
    random_seed: null,
    started_at: null,
    last_tick_at: null,
    message: 'Simulation is stopped.',
    is_simulated: true,
  };

  it('renders start button when simulation is stopped', () => {
    const handleStart = vi.fn();
    const handleStop = vi.fn();

    render(
      <SimulationControls
        status={stoppedStatus}
        onStart={handleStart}
        onStop={handleStop}
        loading={false}
      />
    );

    expect(screen.getByText('STOPPED')).toBeInTheDocument();
    const startBtn = screen.getByRole('button', { name: /start simulation/i });
    expect(startBtn).toBeInTheDocument();

    fireEvent.click(startBtn);
    expect(handleStart).toHaveBeenCalledWith({
      vehicle_count: 25,
      interval_seconds: 3.0,
      random_seed: undefined,
    });
  });

  it('renders stop button when simulation is running', () => {
    const runningStatus: SimulationStatus = {
      ...stoppedStatus,
      is_running: true,
      message: 'Simulation is active.',
    };
    const handleStart = vi.fn();
    const handleStop = vi.fn();

    render(
      <SimulationControls
        status={runningStatus}
        onStart={handleStart}
        onStop={handleStop}
        loading={false}
      />
    );

    expect(screen.getByText('RUNNING')).toBeInTheDocument();
    const stopBtn = screen.getByRole('button', { name: /stop simulation/i });
    expect(stopBtn).toBeInTheDocument();

    fireEvent.click(stopBtn);
    expect(handleStop).toHaveBeenCalledTimes(1);
  });
});
