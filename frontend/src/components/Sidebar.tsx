import { NavLink, useLocation } from 'react-router-dom';
import {
  ShieldCheck,
  MessageSquare,
  History,
  BarChart3,
  BookOpen,
} from 'lucide-react';
import './Sidebar.css';

const NAV_ITEMS = [
  { to: '/',           icon: MessageSquare, label: 'Ask / Audit' },
  { to: '/history',    icon: History,       label: 'History' },
  { to: '/evaluation', icon: BarChart3,     label: 'Evaluation' },
  { to: '/guide',      icon: BookOpen,      label: 'Guide' },
];

export function Sidebar() {
  const location = useLocation();

  return (
    <aside className="sidebar" aria-label="Main navigation">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <ShieldCheck size={20} strokeWidth={2.5} />
        </div>
        <div className="sidebar-logo-text">
          <span className="sidebar-brand">TruthGuard</span>
          <span className="sidebar-tagline">AI Verification</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <div className="sidebar-nav-label">Navigation</div>
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => {
          const isActive =
            to === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(to);

          return (
            <NavLink
              key={to}
              to={to}
              className={`sidebar-link ${isActive ? 'active' : ''}`}
            >
              <Icon size={18} strokeWidth={isActive ? 2.2 : 1.8} />
              <span>{label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-footer-line">
          <ShieldCheck size={14} />
          <span>Claim-Level NLI Engine</span>
        </div>
        <div className="sidebar-footer-sub">
          DeBERTa-v3 + Gemini + RRF
        </div>
      </div>
    </aside>
  );
}
