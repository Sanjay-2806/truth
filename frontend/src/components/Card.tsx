import type { ReactNode } from 'react';
import './Card.css';

export interface CardProps {
  title?: string;
  icon?: ReactNode;
  badge?: ReactNode;
  /** Extra class names */
  className?: string;
  children: ReactNode;
}

export function Card({ title, icon, badge, className = '', children }: CardProps) {
  return (
    <div className={`card animate-fade-in ${className}`}>
      {title && (
        <div className="card-header">
          <div className="card-header-left">
            {icon && <span className="card-icon">{icon}</span>}
            <h3 className="card-title">{title}</h3>
          </div>
          {badge && <div className="card-header-right">{badge}</div>}
        </div>
      )}
      <div className="card-body">{children}</div>
    </div>
  );
}
