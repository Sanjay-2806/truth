import { useEffect, useState } from 'react';
import { Activity } from 'lucide-react';
import { apiGetHealth } from '../hooks/useApi';
import type { HealthInfo } from '../types';
import './TopBar.css';

interface TopBarProps {
  title: string;
  subtitle?: string;
}

export function TopBar({ title, subtitle }: TopBarProps) {
  const [health, setHealth] = useState<HealthInfo | null>(null);

  useEffect(() => {
    apiGetHealth().then(setHealth);
    const interval = setInterval(() => apiGetHealth().then(setHealth), 30000);
    return () => clearInterval(interval);
  }, []);

  const deviceName =
    health?.device?.selected_device || health?.device?.device || 'Connecting…';

  return (
    <header className="topbar">
      <div className="topbar-left">
        <h1 className="topbar-title">{title}</h1>
        {subtitle && <span className="topbar-subtitle">{subtitle}</span>}
      </div>

      <div className="topbar-right">
        <div className={`health-badge ${health ? 'online' : 'offline'}`}>
          <span className="health-dot" />
          <span className="health-label">
            {health ? `Online · ${deviceName.toUpperCase()}` : 'Connecting…'}
          </span>
          {!health && <Activity size={14} className="animate-spin" />}
        </div>
      </div>
    </header>
  );
}
