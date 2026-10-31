import React, { ReactNode } from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtext?: string;
  icon?: ReactNode;
}

export const MetricCard: React.FC<MetricCardProps> = ({ title, value, subtext, icon }) => {
  return (
    <div className="metric-card" data-testid="metric-card">
      <div className="metric-header">
        <span>{title}</span>
        {icon && <span style={{ opacity: 0.8 }}>{icon}</span>}
      </div>
      <div className="metric-value">{value}</div>
      {subtext && <div className="metric-subtext">{subtext}</div>}
    </div>
  );
};
