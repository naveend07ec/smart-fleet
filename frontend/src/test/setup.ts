import '@testing-library/jest-dom';
import { vi } from 'vitest';
import React from 'react';

// Mock react-chartjs-2 components so JSDOM doesn't crash on canvas node properties
vi.mock('react-chartjs-2', () => ({
  Bar: () => React.createElement('div', { 'data-testid': 'mock-bar-chart' }),
  Line: () => React.createElement('div', { 'data-testid': 'mock-line-chart' }),
  Doughnut: () => React.createElement('div', { 'data-testid': 'mock-doughnut-chart' }),
  Pie: () => React.createElement('div', { 'data-testid': 'mock-pie-chart' }),
}));

// Mock window.HTMLCanvasElement.prototype.getContext for Chart.js in jsdom
HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
  fillRect: vi.fn(),
  clearRect: vi.fn(),
  getImageData: vi.fn(),
  putImageData: vi.fn(),
  createImageData: vi.fn(),
  setTransform: vi.fn(),
  drawImage: vi.fn(),
  save: vi.fn(),
  fillText: vi.fn(),
  restore: vi.fn(),
  beginPath: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  closePath: vi.fn(),
  stroke: vi.fn(),
  translate: vi.fn(),
  scale: vi.fn(),
  rotate: vi.fn(),
  arc: vi.fn(),
  fill: vi.fn(),
  measureText: vi.fn().mockReturnValue({ width: 0 }),
  transform: vi.fn(),
  rect: vi.fn(),
  clip: vi.fn(),
});
