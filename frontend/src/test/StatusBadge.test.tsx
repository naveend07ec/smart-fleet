import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../components/StatusBadge';

describe('StatusBadge Component', () => {
  it('renders moving status badge with proper class', () => {
    render(<StatusBadge status="moving" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('moving');
    expect(badge).toHaveTextContent('moving');
  });

  it('renders idle status badge', () => {
    render(<StatusBadge status="idle" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge).toHaveClass('idle');
    expect(badge).toHaveTextContent('idle');
  });

  it('renders offline status badge', () => {
    render(<StatusBadge status="offline" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge).toHaveClass('offline');
    expect(badge).toHaveTextContent('offline');
  });
});
