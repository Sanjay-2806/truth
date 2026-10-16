import type { ReactNode } from 'react';
import { Inbox } from 'lucide-react';
import './EmptyState.css';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
}

export function EmptyState({ icon, title, description }: EmptyStateProps) {
  return (
    <div className="empty-state animate-fade-in">
      <div className="empty-state-icon">
        {icon || <Inbox size={40} strokeWidth={1.2} />}
      </div>
      <h3 className="empty-state-title">{title}</h3>
      {description && (
        <p className="empty-state-desc">{description}</p>
      )}
    </div>
  );
}
