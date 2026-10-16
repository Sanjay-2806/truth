import { CheckCircle, AlertTriangle, XCircle, HelpCircle } from 'lucide-react';
import type { VerificationLabel } from '../types';
import './StatusBadge.css';

interface StatusBadgeProps {
  /** "Verified" | "Unsupported" | "Contradicted" | "Not Applicable" for claims,
   *  or "RELEASED" | "ABSTAINED" for decisions */
  status: VerificationLabel | 'RELEASED' | 'ABSTAINED';
  size?: 'sm' | 'md';
}

const CONFIG: Record<
  string,
  { className: string; icon: typeof CheckCircle; label: string }
> = {
  Verified:   { className: 'status-verified',      icon: CheckCircle,   label: 'Verified' },
  Unsupported:{ className: 'status-unsupported',   icon: HelpCircle,    label: 'Unsupported' },
  Contradicted:{ className: 'status-contradicted', icon: XCircle,       label: 'Contradicted' },
  'Not Applicable': { className: 'status-info',    icon: HelpCircle,    label: 'N/A' },
  RELEASED:   { className: 'status-verified',      icon: CheckCircle,   label: 'Released' },
  ABSTAINED:  { className: 'status-unsupported',   icon: AlertTriangle, label: 'Abstained' },
};

export function StatusBadge({ status, size = 'sm' }: StatusBadgeProps) {
  const cfg = CONFIG[status] || CONFIG['Not Applicable'];
  const Icon = cfg.icon;
  const iconSize = size === 'sm' ? 12 : 14;

  return (
    <span className={`status-badge ${cfg.className} status-${size}`}>
      <Icon size={iconSize} strokeWidth={2.5} />
      <span>{cfg.label}</span>
    </span>
  );
}
