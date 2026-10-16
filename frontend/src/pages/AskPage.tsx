import { useState } from 'react';
import {
  Search,
  Activity,
  AlertTriangle,
  CheckCircle2,
  BookOpen,
  Clock,
  HelpCircle,
  XCircle,
  Zap,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Code2,
  FileText,
  ShieldAlert,
  ShieldCheck,
  ExternalLink,
} from 'lucide-react';
import { TopBar } from '../components/TopBar';
import { Card } from '../components/Card';
import { StatusBadge } from '../components/StatusBadge';
import { RiskGauge } from '../components/RiskGauge';
import { apiAsk } from '../hooks/useApi';
import { SAMPLE_QUESTIONS, MODE_LABELS, RISK_THRESHOLD } from '../lib/constants';
import type { AskResponse, ClaimVerificationResult } from '../types';
import type { AppMode } from '../lib/constants';
import './AskPage.css';

export function AskPage() {
  const [question, setQuestion] = useState('');
  const [mode, setMode] = useState<AppMode>('truthguard');
  const [loading, setLoading] = useState(false);
  const [currentRun, setCurrentRun] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // UI Interactive States
  const [claimFilter, setClaimFilter] = useState<'ALL' | 'VERIFIED' | 'UNSUPPORTED' | 'CONTRADICTED'>('ALL');
  const [expandedClaimId, setExpandedClaimId] = useState<string | null>(null);
  const [highlightedPassageId, setHighlightedPassageId] = useState<string | null>(null);
  const [copiedAnswer, setCopiedAnswer] = useState(false);
  const [showRawJson, setShowRawJson] = useState(false);

  const handleAsk = async (queryText?: string) => {
    const q = (queryText || question).trim();
    if (!q) return;

    setLoading(true);
    setError(null);
    setHighlightedPassageId(null);
    setExpandedClaimId(null);
    setShowRawJson(false);

    try {
      const data = await apiAsk(q, mode);
      setCurrentRun(data);
    } catch (err: any) {
      setError(err.message || 'Error executing audit request');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedAnswer(true);
    setTimeout(() => setCopiedAnswer(false), 2000);
  };

  const getLabelIcon = (label: string) => {
    switch (label.toLowerCase()) {
      case 'verified':     return <CheckCircle2 size={15} className="claim-icon-v" />;
      case 'contradicted': return <XCircle size={15} className="claim-icon-c" />;
      default:             return <HelpCircle size={15} className="claim-icon-u" />;
    }
  };

  // Counts for claim filter tabs
  const verifiedCount = currentRun?.claims.filter((c) => c.label.toLowerCase() === 'verified').length || 0;
  const unsupportedCount = currentRun?.claims.filter((c) => c.label.toLowerCase() === 'unsupported').length || 0;
  const contradictedCount = currentRun?.claims.filter((c) => c.label.toLowerCase() === 'contradicted').length || 0;

  const filteredClaims = currentRun?.claims.filter((c) => {
    if (claimFilter === 'ALL') return true;
    return c.label.toLowerCase() === claimFilter.toLowerCase();
  }) || [];

  // Total latency
  const totalTiming = currentRun
    ? Object.values(currentRun.timings_ms).reduce((a, b) => a + b, 0)
    : 0;

  return (
    <>
      <TopBar
        title="Ask & Audit"
        subtitle="Sairam Autonomous Academic Regulations 2024 · Dual-Grounding Fact Verifier"
      />

      <div className="app-content">
        <div className="content-container">

          {/* ── Query Card ── */}
          <Card className="query-card animate-fade-in-up">
            {/* Mode Pills */}
            <div className="mode-selector-wrap">
              <span className="mode-label-hint">Pipeline Mode:</span>
              <div className="mode-selector">
                {(Object.entries(MODE_LABELS) as [AppMode, string][]).map(
                  ([key, label]) => (
                    <button
                      key={key}
                      className={`mode-pill ${mode === key ? 'active' : ''}`}
                      onClick={() => setMode(key)}
                    >
                      {label}
                    </button>
                  ),
                )}
              </div>
            </div>

            {/* Input + Button */}
            <div className="query-row">
              <input
                type="text"
                className="input query-input"
                placeholder="Ask any regulation question — attendance, grading, arrears, fast-track, honors…"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
                disabled={loading}
              />
              <button
                className="btn btn-primary btn-lg ask-btn"
                onClick={() => handleAsk()}
                disabled={loading || !question.trim()}
              >
                {loading ? (
                  <Activity size={18} className="animate-spin" />
                ) : (
                  <Search size={18} />
                )}
                <span>{loading ? 'Verifying…' : 'Audit'}</span>
              </button>
            </div>

            {/* Sample Questions */}
            <div className="samples">
              <span className="samples-label">Try:</span>
              {SAMPLE_QUESTIONS.map((q, i) => (
                <button
                  key={i}
                  className="sample-chip"
                  onClick={() => {
                    setQuestion(q);
                    handleAsk(q);
                  }}
                  disabled={loading}
                >
                  {q.length > 58 ? q.slice(0, 58) + '…' : q}
                </button>
              ))}
            </div>
          </Card>

          {/* ── Error Banner ── */}
          {error && (
            <div className="error-banner animate-fade-in">
              <AlertTriangle size={18} />
              <div className="error-body">
                <strong>Audit Error:</strong> {error}
              </div>
            </div>
          )}

          {/* ── Results Area ── */}
          {currentRun && (
            <div className="results-area animate-fade-in-up">

              {/* 1. Decision Banner */}
              <div
                className={`decision-banner ${currentRun.abstained ? 'decision-abstained' : 'decision-released'}`}
              >
                <div className="decision-left">
                  <div className="decision-icon-wrap">
                    {currentRun.abstained ? (
                      <ShieldAlert size={28} />
                    ) : (
                      <ShieldCheck size={28} />
                    )}
                  </div>
                  <div className="decision-details">
                    <div className="decision-headline">
                      <h2>
                        {currentRun.abstained
                          ? 'Answer Withheld for Safety'
                          : 'Verified Answer Released'}
                      </h2>
                      <StatusBadge
                        status={currentRun.abstained ? 'ABSTAINED' : 'RELEASED'}
                        size="md"
                      />
                    </div>
                    <p className="decision-explanation">
                      {currentRun.reason_explanation}
                    </p>

                    {/* Decision Factors Checklist */}
                    <div className="decision-checklist">
                      <div className={`checklist-item ${currentRun.risk_score <= RISK_THRESHOLD ? 'item-pass' : 'item-fail'}`}>
                        {currentRun.risk_score <= RISK_THRESHOLD ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
                        <span>
                          Risk Score: <strong>{(currentRun.risk_score * 100).toFixed(1)}%</strong> (threshold: {(RISK_THRESHOLD * 100).toFixed(0)}%)
                        </span>
                      </div>

                      <div className={`checklist-item ${contradictedCount === 0 ? 'item-pass' : 'item-fail'}`}>
                        {contradictedCount === 0 ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
                        <span>
                          Contradicted Claims: <strong>{contradictedCount}</strong>
                        </span>
                      </div>

                      <div className={`checklist-item ${unsupportedCount === 0 ? 'item-pass' : 'item-warn'}`}>
                        {unsupportedCount === 0 ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}
                        <span>
                          Unsupported Claims: <strong>{unsupportedCount}</strong>
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="decision-right">
                  <RiskGauge value={currentRun.risk_score} size={105} />
                  <span className="gauge-caption">Total Risk Score</span>
                </div>
              </div>

              {/* 2. Answer Section */}
              <Card
                title={currentRun.abstained ? 'Unverified / Flagged Answer' : 'Audited Answer'}
                icon={<BookOpen size={16} />}
                badge={
                  currentRun.answer ? (
                    <button
                      className="copy-btn"
                      onClick={() => copyToClipboard(currentRun.answer || '')}
                      title="Copy Answer"
                    >
                      {copiedAnswer ? <Check size={14} className="copied-icon" /> : <Copy size={14} />}
                      <span>{copiedAnswer ? 'Copied' : 'Copy'}</span>
                    </button>
                  ) : undefined
                }
              >
                {currentRun.abstained && (
                  <div className="abstain-warning-box">
                    <AlertTriangle size={16} />
                    <span>
                      This response was withheld from students/faculty because it contains contradicted or unverified factual claims according to Sri Sairam Autonomous Regulations 2024. Review claims below.
                    </span>
                  </div>
                )}
                <div className={`answer-box ${currentRun.abstained ? 'answer-withheld-text' : ''}`}>
                  <p className="answer-text">{currentRun.answer || 'No textual answer generated.'}</p>
                </div>
              </Card>

              {/* 3. Claim-Level Verification */}
              {currentRun.claims.length > 0 && (
                <Card
                  title={`Claim-Level Verification`}
                  icon={<Zap size={16} />}
                  badge={
                    <div className="claim-filter-tabs">
                      <button
                        className={`filter-pill ${claimFilter === 'ALL' ? 'active' : ''}`}
                        onClick={() => setClaimFilter('ALL')}
                      >
                        All ({currentRun.claims.length})
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
                        No claims in this category.
                      </div>
                    ) : (
                      filteredClaims.map((claim: ClaimVerificationResult, idx: number) => {
                        const isExpanded = expandedClaimId === claim.claim_id || (expandedClaimId === null && idx === 0);
                        return (
                          <div
                            key={claim.claim_id}
                            className={`claim-row claim-${claim.label.toLowerCase()}`}
                          >
                            <div
                              className="claim-header-interactive"
                              onClick={() => setExpandedClaimId(isExpanded ? '__none__' : claim.claim_id)}
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

                            {/* Detailed Evidence Accordion */}
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
                                            document.getElementById('passages-section')?.scrollIntoView({ behavior: 'smooth' });
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

              {/* 4. Retrieved Passages */}
              {currentRun.passages.length > 0 && (
                <div id="passages-section">
                  <Card
                    title={`Retrieved Passages (${currentRun.passages.length})`}
                    icon={<FileText size={16} />}
                  >
                    <div className="passages-list">
                      {currentRun.passages.map((p, idx) => {
                        const isHighlighted = highlightedPassageId === p.passage_id;
                        return (
                          <div
                            key={idx}
                            id={`passage-${p.passage_id}`}
                            className={`passage-row ${isHighlighted ? 'passage-highlighted' : ''}`}
                          >
                            <div className="passage-header">
                              <span className="passage-id">
                                <strong>{p.location.section_heading || p.passage_id}</strong>
                                <span className="passage-page"> · Page {p.location.page}</span>
                              </span>
                              <span className="passage-score">
                                Relevance: {(p.score).toFixed(4)}
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

              {/* 5. Pipeline Trace Visualizer */}
              <Card
                title={`Pipeline Trace & Latency (${totalTiming.toFixed(0)} ms total)`}
                icon={<Clock size={16} />}
                badge={
                  <button
                    className="json-toggle-btn"
                    onClick={() => setShowRawJson(!showRawJson)}
                  >
                    <Code2 size={14} />
                    <span>{showRawJson ? 'Hide JSON' : 'Inspect Run JSON'}</span>
                  </button>
                }
              >
                {/* Pipeline visual stepper */}
                <div className="pipeline-stepper">
                  {[
                    { name: '1. Retrieval', key: 'retrieve_ms', desc: 'Hybrid BM25 + Dense' },
                    { name: '2. Generation', key: 'generate_ms', desc: 'Grounding LLM' },
                    { name: '3. Extraction', key: 'extract_ms', desc: 'Atomic Claim Parser' },
                    { name: '4. Verification', key: 'verify_ms', desc: 'DeBERTa NLI Cross' },
                    { name: '5. Decision', key: 'decision_ms', desc: 'Risk Aggregation Gate' },
                  ].map(({ name, key, desc }, sIdx) => {
                    const time = currentRun.timings_ms[key] || 0;
                    const percent = totalTiming > 0 ? (time / totalTiming) * 100 : 20;
                    return (
                      <div key={key} className="pipeline-step-box">
                        <div className="step-num-bar">
                          <span className="step-badge">{sIdx + 1}</span>
                          <span className="step-time">{time} ms</span>
                        </div>
                        <div className="step-name">{name.replace(/^\d+\.\s*/, '')}</div>
                        <div className="step-desc">{desc}</div>
                        <div className="step-progress-track">
                          <div
                            className="step-progress-fill"
                            style={{ width: `${Math.max(percent, 8)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Raw JSON toggle */}
                {showRawJson && (
                  <div className="raw-json-viewer animate-fade-in">
                    <div className="raw-json-header">
                      <span>Full Run Payload (Run ID: {currentRun.run_id})</span>
                      <button
                        className="btn-text-sm"
                        onClick={() => copyToClipboard(JSON.stringify(currentRun, null, 2))}
                      >
                        <Copy size={12} /> Copy JSON
                      </button>
                    </div>
                    <pre className="raw-json-content">
                      {JSON.stringify(currentRun, null, 2)}
                    </pre>
                  </div>
                )}
              </Card>

            </div>
          )}
        </div>
      </div>
    </>
  );
}
