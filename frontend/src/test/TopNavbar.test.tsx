import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TopNavbar } from '../components/TopNavbar';

describe('TopNavbar Component with Security & Privacy Dropdown', () => {
  it('renders primary navigation items and the Security & Privacy dropdown trigger', () => {
    const handleTabChange = vi.fn();
    render(
      <TopNavbar
        currentTab="dashboard"
        onTabChange={handleTabChange}
        isSimRunning={false}
      />
    );

    expect(screen.getByText('Fleet Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Vehicle Fleet')).toBeInTheDocument();
    expect(screen.getByText('Fleet Analytics')).toBeInTheDocument();
    expect(screen.getByText('Security & Privacy')).toBeInTheDocument();
    expect(screen.getByText('Simulator Control')).toBeInTheDocument();
  });

  it('opens dropdown menu when clicking Security & Privacy and displays common names', () => {
    const handleTabChange = vi.fn();
    render(
      <TopNavbar
        currentTab="dashboard"
        onTabChange={handleTabChange}
        isSimRunning={false}
      />
    );

    const dropdownTrigger = screen.getByRole('button', { name: /Security & Privacy/i });
    fireEvent.click(dropdownTrigger);

    // Verify common labels and subtext are visible in the dropdown
    expect(screen.getByText('Security & Quantum Optimization Labs')).toBeInTheDocument();
    expect(screen.getByText('Identity Encryption')).toBeInTheDocument();
    expect(screen.getByText('IBE Security Lab & Key Auth')).toBeInTheDocument();
    expect(screen.getByText('Secure Transmission')).toBeInTheDocument();
    expect(screen.getByText('Encrypted Vehicle Data Tunnel')).toBeInTheDocument();
    expect(screen.getByText('Quantum Privacy')).toBeInTheDocument();
    expect(screen.getByText('Universal BFK09 MBQC Lab')).toBeInTheDocument();
    expect(screen.getByText('QUBO Route Optimizer')).toBeInTheDocument();
  });

  it('calls onTabChange with corresponding tab id when dropdown item is clicked', () => {
    const handleTabChange = vi.fn();
    render(
      <TopNavbar
        currentTab="dashboard"
        onTabChange={handleTabChange}
        isSimRunning={false}
      />
    );

    const dropdownTrigger = screen.getByRole('button', { name: /Security & Privacy/i });
    fireEvent.click(dropdownTrigger);

    const quantumItem = screen.getByRole('menuitem', { name: /Quantum Privacy/i });
    fireEvent.click(quantumItem);

    expect(handleTabChange).toHaveBeenCalledWith('bqc');
  });

  it('displays the active security tab name when a security tab is selected', () => {
    const handleTabChange = vi.fn();
    render(
      <TopNavbar
        currentTab="ibe"
        onTabChange={handleTabChange}
        isSimRunning={true}
      />
    );

    expect(screen.getByText('Security: Identity Encryption')).toBeInTheDocument();
  });
});
