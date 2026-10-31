import React from 'react';

interface StatusBadgeProps {
  status: 'moving' | 'idle' | 'offline' | string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const normStatus = status.toLowerCase();
  return (
    <span className={`status-badge ${normStatus}`} data-testid="status-badge">
      <span className="status-dot" />
      {normStatus}
    </span>
  );
};
