import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  History,
  Clock,
  Search,
  RefreshCw,
  ChevronRight,
  ShieldCheck,
  ShieldAlert,
  Filter,
  ArrowUpDown,
  AlertTriangle,
} from 'lucide-react';
import { TopBar } from '../components/TopBar';
import { Card } from '../components/Card';
import { StatusBadge } from '../components/StatusBadge';
import { EmptyState } from '../components/EmptyState';
import { apiGetRuns } from '../hooks/useApi';
import { MODE_LABELS } from '../lib/constants';
import type { RunSummary } from '../types';
import './HistoryPage.css';

type SortField = 'created_at' | 'risk_score' | 'question';
type SortDir = 'asc' | 'desc';
type DecisionFilter = 'ALL' | 'RELEASED' | 'ABSTAINED';

export function HistoryPage() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [decisionFilter, setDecisionFilter] = useState<DecisionFilter>('ALL');
  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiGetRuns(50);
      setRuns(data);
    } catch {
      setRuns([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  // Filtering
  const filtered = runs.filter((r) => {
    if (decisionFilter === 'RELEASED' && r.abstained) return false;
    if (decisionFilter === 'ABSTAINED' && !r.abstained) return false;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      return (
        r.question.toLowerCase().includes(term) ||
        r.run_id.toLowerCase().includes(term) ||
        (r.answer_preview || '').toLowerCase().includes(term)
      );
    }
    return true;
  });

  // Sorting
  const sorted = [...filtered].sort((a, b) => {
    let cmp = 0;
    switch (sortField) {
      case 'created_at':
        cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        break;
      case 'risk_score':
        cmp = a.risk_score - b.risk_score;
        break;
      case 'question':
        cmp = a.question.localeCompare(b.question);
        break;
    }
    return sortDir === 'desc' ? -cmp : cmp;
  });

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const releasedCount = runs.filter((r) => !r.abstained).length;
  const abstainedCount = runs.filter((r) => r.abstained).length;

  const formatDate = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return iso;
    }
  };

  return (
    <>
      <TopBar
        title="Run History"
        subtitle={`${runs.length} verification runs recorded`}
      />

      <div className="app-content">
        <div className="content-container">

          {/* Stats Strip */}
          <div className="history-stats animate-fade-in-up">
            <div className="stat-card">
              <div className="stat-icon stat-icon-total">
                <History size={18} />
              </div>
              <div>
                <span className="stat-value">{runs.length}</span>
                <span className="stat-label">Total Runs</span>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon stat-icon-released">
                <ShieldCheck size={18} />
              </div>
              <div>
                <span className="stat-value">{releasedCount}</span>
                <span className="stat-label">Released</span>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon stat-icon-abstained">
                <ShieldAlert size={18} />
              </div>
              <div>
                <span className="stat-value">{abstainedCount}</span>
                <span className="stat-label">Withheld</span>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon stat-icon-risk">
                <AlertTriangle size={18} />
              </div>
              <div>
                <span className="stat-value">
                  {runs.length > 0
                    ? (
                        (runs.reduce((s, r) => s + r.risk_score, 0) / runs.length) *
                        100
                      ).toFixed(1)
                    : '—'}
                  <span className="stat-unit">%</span>
                </span>
                <span className="stat-label">Avg Risk</span>
              </div>
            </div>
          </div>

          {/* Toolbar */}
          <Card className="history-toolbar animate-fade-in-up">
            <div className="toolbar-row">
              <div className="toolbar-left">
                <div className="search-wrap">
                  <Search size={15} className="search-icon" />
                  <input
                    type="text"
                    className="input search-input"
                    placeholder="Search questions, run IDs…"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>
                <div className="decision-filter-pills">
                  <Filter size={13} className="filter-icon" />
                  {(['ALL', 'RELEASED', 'ABSTAINED'] as DecisionFilter[]).map(
                    (f) => (
                      <button
                        key={f}
                        className={`filter-pill ${decisionFilter === f ? 'active' : ''} ${
                          f === 'RELEASED' ? 'filter-pill-v' : f === 'ABSTAINED' ? 'filter-pill-u' : ''
                        }`}
                        onClick={() => setDecisionFilter(f)}
                      >
                        {f === 'ALL' ? `All (${runs.length})` : f === 'RELEASED' ? `Released (${releasedCount})` : `Withheld (${abstainedCount})`}
                      </button>
                    ),
                  )}
                </div>
              </div>
              <button className="btn btn-ghost refresh-btn" onClick={fetchRuns} disabled={loading}>
                <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
                <span>Refresh</span>
              </button>
            </div>
          </Card>

          {/* Runs Table */}
          {sorted.length === 0 && !loading ? (
            <EmptyState
              icon={<History size={40} strokeWidth={1.2} />}
              title="No Runs Found"
              description={
                searchTerm || decisionFilter !== 'ALL'
                  ? 'No verification runs match your current filters. Try adjusting search or filter criteria.'
                  : 'No verification runs recorded yet. Go to the Ask & Audit page to submit your first query.'
              }
            />
          ) : (
            <div className="runs-table-wrap animate-fade-in-up">
              <table className="runs-table">
                <thead>
                  <tr>
                    <th className="th-decision">Decision</th>
                    <th
                      className="th-question sortable"
                      onClick={() => toggleSort('question')}
                    >
                      Question
                      {sortField === 'question' && (
                        <ArrowUpDown size={12} className="sort-icon" />
                      )}
                    </th>
                    <th className="th-mode">Mode</th>
                    <th
                      className="th-risk sortable"
                      onClick={() => toggleSort('risk_score')}
                    >
                      Risk
                      {sortField === 'risk_score' && (
                        <ArrowUpDown size={12} className="sort-icon" />
                      )}
                    </th>
                    <th
                      className="th-date sortable"
                      onClick={() => toggleSort('created_at')}
                    >
                      Date
                      {sortField === 'created_at' && (
                        <ArrowUpDown size={12} className="sort-icon" />
                      )}
                    </th>
                    <th className="th-action"></th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((run) => (
                    <tr
                      key={run.run_id}
                      className="run-row"
                      onClick={() => navigate(`/history/${run.run_id}`)}
                    >
                      <td className="td-decision">
                        <StatusBadge
                          status={run.abstained ? 'ABSTAINED' : 'RELEASED'}
                          size="sm"
                        />
                      </td>
                      <td className="td-question">
                        <span className="question-text">
                          {run.question.length > 80
                            ? run.question.slice(0, 80) + '…'
                            : run.question}
                        </span>
                        {run.answer_preview && (
                          <span className="answer-preview">
                            {run.answer_preview.length > 60
                              ? run.answer_preview.slice(0, 60) + '…'
                              : run.answer_preview}
                          </span>
                        )}
                      </td>
                      <td className="td-mode">
                        <span className="mode-tag">
                          {MODE_LABELS[run.mode] || run.mode}
                        </span>
                      </td>
                      <td className="td-risk">
                        <span
                          className={`risk-value ${
                            run.risk_score > 0.25
                              ? 'risk-high'
                              : run.risk_score > 0.1
                              ? 'risk-mid'
                              : 'risk-low'
                          }`}
                        >
                          {(run.risk_score * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="td-date">
                        <span className="date-text">
                          <Clock size={12} />
                          {formatDate(run.created_at)}
                        </span>
                      </td>
                      <td className="td-action">
                        <ChevronRight size={16} className="chevron" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Loading state */}
          {loading && (
            <div className="loading-strip animate-fade-in">
              <RefreshCw size={16} className="animate-spin" />
              <span>Loading verification history…</span>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
