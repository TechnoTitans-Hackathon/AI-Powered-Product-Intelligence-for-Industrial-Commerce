import React from 'react';
import { ConfidenceLevel } from '../types';
import { ShieldCheck, ShieldAlert, AlertTriangle, ShieldX } from 'lucide-react';

interface Props {
  level: ConfidenceLevel | string;
  showIcon?: boolean;
}

export const ConfidenceBadge: React.FC<Props> = ({ level, showIcon = true }) => {
  const normLevel = (level || 'LOW').toUpperCase();

  if (normLevel === 'HIGH') {
    return (
      <span className="badge badge-high" title="High confidence backed by direct evidence">
        {showIcon && <ShieldCheck size={12} />}
        HIGH
      </span>
    );
  }

  if (normLevel === 'MEDIUM') {
    return (
      <span className="badge badge-medium" title="Medium confidence derived from contextual sources">
        {showIcon && <ShieldAlert size={12} />}
        MEDIUM
      </span>
    );
  }

  if (normLevel === 'LOW') {
    return (
      <span className="badge badge-low" title="Low confidence - sparse evidence available">
        {showIcon && <AlertTriangle size={12} />}
        LOW
      </span>
    );
  }

  return (
    <span className="badge badge-conflict" title="Conflict or critical discrepancy detected">
      {showIcon && <ShieldX size={12} />}
      CONFLICT
    </span>
  );
};
