import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Copy,
  Check,
  BookOpen,
  FileText,
  Clock,
  Zap,
  Code,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Cpu,
  Layers,
  HelpCircle,
  RefreshCw,
} from 'lucide-react';
import { TopBar } from '../components/TopBar';
import { Card } from '../components/Card';
import { StatusBadge } from '../components/StatusBadge';
import { RiskGauge } from '../components/RiskGauge';
import { EmptyState } from '../components/EmptyState';
import { apiGetRun } from '../hooks/useApi';
import { RISK_THRESHOLD, MODE_LABELS } from '../lib/constants';
import type { AskResponse, ClaimVerificationResult } from '../types';
import './RunDetailPage.css';

type ClaimFilter = 'ALL' | 'VERIFIED' | 'UNSUPPORTED' | 'CONTRADICTED';

export function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();

  const [run, setRun] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [copiedAnswer, setCopiedAnswer] = useState(false);
  const [copiedJson, setCopiedJson] = useState(false);
  const [copiedId, setCopiedId] = useState(false);
  const [showRawJson, setShowRawJson] = useState(false);
  const [claimFilter, setClaimFilter] = useState<ClaimFilter>('ALL');
  const [expandedClaimId, setExpandedClaimId] = useState<string | null>(null);
  const [highlightedPassageId, setHighlightedPassageId] = useState<string | null>(null);

  const loadRun = useCallback(async () => {
    if (!runId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiGetRun(runId);
      setRun(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load run details');
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    loadRun();
  }, [loadRun]);

  const copyToClipboard = async (text: string, type: 'answer' | 'json' | 'id') => {
    try {
      await navigator.clipboard.writeText(text);
      if (type === 'answer') {
        setCopiedAnswer(true);
        setTimeout(() => setCopiedAnswer(false), 2000);
      } else if (type === 'json') {
        setCopiedJson(true);
        setTimeout(() => setCopiedJson(false), 2000);
      } else if (type === 'id') {
        setCopiedId(true);
        setTimeout(() => setCopiedId(false), 2000);
      }
    } catch {
      // fallback
    }
  };

  if (loading) {
    return (
      <>
        <TopBar title="Run Audit Details" subtitle="Loading verification record…" />
        <div className="app-content">
          <div className="content-container loading-container">
            <RefreshCw size={24} className="animate-spin text-accent" />
            <span className="loading-text">Loading run audit {runId}…</span>
          </div>
        </div>
      </>
    );
  }

  if (error || !run) {
    return (
      <>
        <TopBar title="Run Audit Details" subtitle="Error loading record" />
        <div className="app-content">
          <div className="content-container">
            <button className="btn btn-ghost back-btn" onClick={() => navigate('/history')}>
              <ArrowLeft size={16} />
              <span>Back to History</span>
            </button>
            <EmptyState
              icon={<AlertTriangle size={40} className="text-danger" />}
              title="Run Not Found"
              description={error || 'The requested verification run could not be found or loaded.'}
            />
          </div>
        </div>
      </>
    );
  }

  // Claim counts
  const claims = run.claims || [];
  const verifiedCount = claims.filter((c) => c.label === 'Verified').length;
  const unsupportedCount = claims.filter((c) => c.label === 'Unsupported').length;
  const contradictedCount = claims.filter((c) => c.label === 'Contradicted').length;

  const filteredClaims = claims.filter((c) => {
    if (claimFilter === 'VERIFIED') return c.label === 'Verified';
    if (claimFilter === 'UNSUPPORTED') return c.label === 'Unsupported';
    if (claimFilter === 'CONTRADICTED') return c.label === 'Contradicted';
    return true;
  });

  const getLabelIcon = (label: string) => {
    switch (label) {
      case 'Verified':
        return <CheckCircle2 size={15} className="claim-icon-v" />;
      case 'Unsupported':
        return <AlertTriangle size={15} className="claim-icon-u" />;
      case 'Contradicted':
        return <XCircle size={15} className="claim-icon-c" />;
      default:
        return null;
    }
  };

  const totalTiming = Object.values(run.timings_ms || {}).reduce((a, b) => a + b, 0);

  return (
    <>
      <TopBar
        title="Run Audit Record"
        subtitle={`Audit ID: ${run.run_id}`}
      />

      <div className="app-content">
        <div className="content-container run-detail-container">

          {/* Navigation Bar */}
          <div className="detail-nav-bar animate-fade-in">
            <button className="btn btn-ghost back-btn" onClick={() => navigate('/history')}>
              <ArrowLeft size={16} />
              <span>Back to History</span>
            </button>

            <div className="detail-meta-tags">
              <span className="meta-pill mode-pill-static">
                <Layers size={13} />
                {MODE_LABELS[run.mode] || run.mode}
              </span>

              <button
                className="meta-pill copy-id-pill"
                onClick={() => copyToClipboard(run.run_id, 'id')}
                title="Click to copy full Run ID"
              >
                {copiedId ? <Check size={13} className="text-success" /> : <Copy size={13} />}
                <span>ID: {run.run_id.slice(0, 12)}…</span>
              </button>

              {totalTiming > 0 && (
                <span className="meta-pill">
                  <Clock size={13} />
                  {totalTiming.toFixed(0)} ms total
                </span>
              )}
            </div>
          </div>

          {/* 1. Decision Banner */}
          <div
            className={`decision-banner animate-fade-in-up ${
              run.abstained ? 'decision-abstained' : 'decision-released'
            }`}
          >
            <div className="decision-left">
              <div className="decision-icon-wrap">
                {run.abstained ? (
                  <ShieldAlert size={28} />
                ) : (
                  <ShieldCheck size={28} />
                )}
              </div>
              <div className="decision-details">
                <div className="decision-headline">
                  <h2>
                    {run.abstained
                      ? 'Answer Withheld for Safety'
                      : 'Verified Answer Released'}
                  </h2>
                  <StatusBadge
                    status={run.abstained ? 'ABSTAINED' : 'RELEASED'}
                    size="md"
                  />
                </div>
                <p className="decision-explanation">
                  {run.reason_explanation || (run.abstained ? 'Withheld based on risk assessment.' : 'Passed all verification thresholds.')}
                </p>

                {/* Factors Checklist */}
                <div className="decision-checklist">
                  <div
                    className={`checklist-item ${
                      run.risk_score <= RISK_THRESHOLD ? 'item-pass' : 'item-fail'
                    }`}
                  >
                    {run.risk_score <= RISK_THRESHOLD ? (
                      <CheckCircle2 size={13} />
                    ) : (
                      <XCircle size={13} />
                    )}
                    <span>
                      Risk Score: <strong>{(run.risk_score * 100).toFixed(1)}%</strong>{' '}
                      (threshold: {(RISK_THRESHOLD * 100).toFixed(0)}%)
                    </span>
                  </div>

                  <div
                    className={`checklist-item ${
                      contradictedCount === 0 ? 'item-pass' : 'item-fail'
                    }`}
                  >
                    {contradictedCount === 0 ? (
                      <CheckCircle2 size={13} />
                    ) : (
                      <XCircle size={13} />
                    )}
                    <span>
                      Contradicted Claims: <strong>{contradictedCount}</strong>
                    </span>
                  </div>

                  <div
                    className={`checklist-item ${
                      unsupportedCount === 0 ? 'item-pass' : 'item-warn'
                    }`}
                  >
                    {unsupportedCount === 0 ? (
                      <CheckCircle2 size={13} />
                    ) : (
                      <AlertTriangle size={13} />
                    )}
                    <span>
                      Unsupported Claims: <strong>{unsupportedCount}</strong>
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="decision-right">
              <RiskGauge value={run.risk_score} size={105} />
              <span className="gauge-caption">Total Risk Score</span>
            </div>
          </div>

          {/* 2. Original Question Card */}
          <Card
            title="Question Prompt"
            icon={<HelpCircle size={16} />}
            className="animate-fade-in-up"
          >
            <div className="prompt-content">
              <p className="prompt-text">{run.question}</p>
            </div>
          </Card>

          {/* 3. Answer Section */}
          <Card
            title={run.abstained ? 'Unverified / Flagged Answer' : 'Audited Answer'}
            icon={<BookOpen size={16} />}
            className="animate-fade-in-up"
            badge={
              run.answer ? (
                <button
                  className="copy-btn"
                  onClick={() => copyToClipboard(run.answer || '', 'answer')}
                  title="Copy Answer"
                >
                  {copiedAnswer ? <Check size={14} className="copied-icon" /> : <Copy size={14} />}
                  <span>{copiedAnswer ? 'Copied' : 'Copy'}</span>
                </button>
              ) : undefined
            }
          >
            {run.abstained && (
              <div className="abstain-warning-box">
                <AlertTriangle size={16} />
                <span>
                  This response was withheld from users because it contains contradicted or unverified factual claims according to Sri Sairam Autonomous Regulations 2024.
                </span>
              </div>
            )}
            <div className={`answer-box ${run.abstained ? 'answer-withheld-text' : ''}`}>
              <p className="answer-text">
                {run.answer || 'No answer text was generated for this run.'}
              </p>
            </div>
          </Card>

          {/* 4. Claim-Level Verification */}
          {claims.length > 0 && (
            <Card
              title="Claim-Level Verification"
              icon={<Zap size={16} />}
              className="animate-fade-in-up"
              badge={
                <div className="claim-filter-tabs">
                  <button
                    className={`filter-pill ${claimFilter === 'ALL' ? 'active' : ''}`}
                    onClick={() => setClaimFilter('ALL')}
                  >
                    All ({claims.length})
                  </button>
                  <button
                    className={`filter-pill filter-pill-v ${claimFilter === 'VERIFIED' ? 'active' : ''}`}
                    onClick={() => setClaimFilter('VERIFIED')}
                  >
                    Verified ({verifiedCount})
                  </button>
                  <button
                    className={`filter-pill filter-pill-u ${claimFilter === 'UNSUPPORTED' ? 'active' : ''}`}
                    onClick={() => setClaimFilter('UNSUPPORTED')}
                  >
                    Unsupported ({unsupportedCount})
                  </button>
                  <button
                    className={`filter-pill filter-pill-c ${claimFilter === 'CONTRADICTED' ? 'active' : ''}`}
                    onClick={() => setClaimFilter('CONTRADICTED')}
                  >
                    Contradicted ({contradictedCount})
                  </button>
                </div>
              }
            >
              <div className="claims-list">
                {filteredClaims.length === 0 ? (
                  <div className="no-claims-match">
                    No claims match the selected filter.
                  </div>
                ) : (
                  filteredClaims.map((claim: ClaimVerificationResult, idx: number) => {
                    const isExpanded =
                      expandedClaimId === claim.claim_id ||
                      (expandedClaimId === null && idx === 0);

                    return (
                      <div
                        key={claim.claim_id || idx}
                        className={`claim-row claim-${claim.label.toLowerCase()}`}
                      >
                        <div
                          className="claim-header-interactive"
                          onClick={() =>
                            setExpandedClaimId(isExpanded ? '__none__' : claim.claim_id)
                          }
                        >
                          <div className="claim-badges">
                            {getLabelIcon(claim.label)}
                            <StatusBadge status={claim.label} size="sm" />
                            {claim.type && (
                              <span className="pill claim-type-pill">
                                {claim.type}
                              </span>
                            )}
                            {claim.critical && (
                              <span className="pill claim-critical-pill">
                                Critical · w={claim.weight}
                              </span>
                            )}
                          </div>

                          <div className="claim-scores-wrap">
                            <div className="claim-scores">
                              <span className="score score-e" title="Entailment probability">
                                E<sub>i</sub> {(claim.E_i * 100).toFixed(0)}%
                              </span>
                              <span className="score score-k" title="Contradiction probability">
                                K<sub>i</sub> {(claim.K_i * 100).toFixed(0)}%
                              </span>
                            </div>
                            <button className="claim-expand-btn">
                              {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                            </button>
                          </div>
                        </div>

                        <p className="claim-text">{claim.claim_text}</p>

                        {/* Evidence Accordion */}
                        {isExpanded && (
                          <div className="claim-expanded-details animate-fade-in">
                            {claim.evidence_text ? (
                              <div className="evidence-box">
                                <div className="evidence-header">
                                  <div className="evidence-title">
                                    <BookOpen size={14} />
                                    <span>
                                      Citation: <strong>{claim.evidence_passage_id || 'Academic Regulations'}</strong>
                                    </span>
                                  </div>
                                  {claim.evidence_passage_id && (
                                    <button
                                      className="link-btn"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setHighlightedPassageId(claim.evidence_passage_id || null);
                                        document
                                          .getElementById('passages-section')
                                          ?.scrollIntoView({ behavior: 'smooth' });
                                      }}
                                    >
                                      <span>Jump to Passage</span>
                                      <ExternalLink size={12} />
                                    </button>
                                  )}
                                </div>
                                <p className="evidence-text">
                                  "{claim.evidence_text}"
                                </p>
                              </div>
                            ) : (
                              <div className="no-evidence-alert">
                                <AlertTriangle size={14} />
                                <span>No direct supporting passage matched this claim in the regulation corpus.</span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </Card>
          )}

          {/* 5. Retrieved Passages */}
          {run.passages && run.passages.length > 0 && (
            <div id="passages-section">
              <Card
                title={`Retrieved Passages (${run.passages.length})`}
                icon={<FileText size={16} />}
                className="animate-fade-in-up"
              >
                <div className="passages-list">
                  {run.passages.map((p, idx) => {
                    const isHighlighted = highlightedPassageId === p.passage_id;
                    return (
                      <div
                        key={p.passage_id || idx}
                        id={`passage-${p.passage_id}`}
                        className={`passage-row ${isHighlighted ? 'passage-highlighted' : ''}`}
                      >
                        <div className="passage-header">
                          <span className="passage-id">
                            <strong>{p.location?.section_heading || p.passage_id}</strong>
                            {p.location?.page !== undefined && (
                              <span className="passage-page"> · Page {p.location.page}</span>
                            )}
                          </span>
                          <span className="passage-score">
                            Relevance: {p.score !== undefined ? p.score.toFixed(4) : '—'}
                          </span>
                        </div>
                        <p className="passage-text">{p.text}</p>
                      </div>
                    );
                  })}
                </div>
              </Card>
            </div>
          )}

          {/* 6. Execution Telemetry & Parameters */}
          <Card
            title="Execution Telemetry & Parameters"
            icon={<Cpu size={16} />}
            className="animate-fade-in-up"
            badge={
              <button
                className="json-toggle-btn"
                onClick={() => setShowRawJson(!showRawJson)}
              >
                <Code size={13} />
                <span>{showRawJson ? 'Hide Raw JSON' : 'Inspect Raw JSON'}</span>
              </button>
            }
          >
            {/* Timings Stepper */}
            {run.timings_ms && Object.keys(run.timings_ms).length > 0 && (
              <div className="pipeline-stepper">
                {Object.entries(run.timings_ms).map(([key, ms], idx) => {
                  const pct = totalTiming > 0 ? (ms / totalTiming) * 100 : 0;
                  return (
                    <div key={key} className="pipeline-step-box">
                      <div className="step-num-bar">
                        <span className="step-badge">{idx + 1}</span>
                        <span className="step-time">{ms.toFixed(0)} ms</span>
                      </div>
                      <span className="step-name">
                        {key.replace(/_ms$/, '').replace(/_/g, ' ').toUpperCase()}
                      </span>
                      <span className="step-desc">
                        {pct.toFixed(0)}% of runtime
                      </span>
                      <div className="step-progress-track">
                        <div
                          className="step-progress-fill"
                          style={{ width: `${Math.max(pct, 5)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Token Usage & Parameters Strip */}
            <div className="telemetry-info-grid">
              {run.token_usage && Object.keys(run.token_usage).length > 0 && (
                <div className="telemetry-subcard">
                  <span className="telemetry-subhead">Token Consumption</span>
                  <div className="telemetry-kv-list">
                    {Object.entries(run.token_usage).map(([k, v]) => (
                      <div key={k} className="telemetry-kv">
                        <span className="telemetry-k">{k.replace(/_/g, ' ')}:</span>
                        <span className="telemetry-v">{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {run.parameters && Object.keys(run.parameters).length > 0 && (
                <div className="telemetry-subcard">
                  <span className="telemetry-subhead">Guardrail Hyperparameters</span>
                  <div className="telemetry-kv-list">
                    {Object.entries(run.parameters)
                      .filter(([_, v]) => typeof v === 'number' || typeof v === 'string')
                      .map(([k, v]) => (
                        <div key={k} className="telemetry-kv">
                          <span className="telemetry-k">{k}:</span>
                          <span className="telemetry-v">{String(v)}</span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>

            {/* Raw JSON viewer */}
            {showRawJson && (
              <div className="raw-json-viewer animate-fade-in">
                <div className="raw-json-header">
                  <span>Full Response Payload ({run.run_id})</span>
                  <button
                    className="btn-text-sm"
                    onClick={() => copyToClipboard(JSON.stringify(run, null, 2), 'json')}
                  >
                    {copiedJson ? <Check size={12} /> : <Copy size={12} />}
                    <span>{copiedJson ? 'Copied' : 'Copy Payload'}</span>
                  </button>
                </div>
                <pre className="raw-json-content">
                  {JSON.stringify(run, null, 2)}
                </pre>
              </div>
            )}
          </Card>

        </div>
      </div>
    </>
  );
}
