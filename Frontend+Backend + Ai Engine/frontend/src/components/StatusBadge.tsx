import React from 'react';
import { ProductStatus } from '../types';
import { CheckCircle2, Clock, AlertOctagon, HelpCircle, XCircle } from 'lucide-react';

interface Props {
  status: ProductStatus | string;
}

export const StatusBadge: React.FC<Props> = ({ status }) => {
  const norm = (status || '').toLowerCase();

  if (norm === 'verified') {
    return (
      <span className="badge badge-verified">
        <CheckCircle2 size={12} />
        Verified
      </span>
    );
  }

  if (norm === 'needs_review' || norm === 'review_required') {
    return (
      <span className="badge badge-needs-review">
        <HelpCircle size={12} />
        Needs Review
      </span>
    );
  }

  if (norm === 'conflicting') {
    return (
      <span className="badge badge-conflict">
        <AlertOctagon size={12} />
        Conflicting
      </span>
    );
  }

  if (norm === 'processing' || norm === 'queued') {
    return (
      <span className="badge badge-processing">
        <Clock size={12} />
        Processing
      </span>
    );
  }

  return (
    <span className="badge badge-failed">
      <XCircle size={12} />
      {status || 'Failed'}
    </span>
  );
};
