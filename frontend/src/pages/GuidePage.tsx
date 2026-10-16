import { useState } from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Cpu,
  FileText,
  HelpCircle,
  Zap,
  Scale,
  Calculator,
  Sliders,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { TopBar } from '../components/TopBar';
import { Card } from '../components/Card';
import { StatusBadge } from '../components/StatusBadge';
import { RISK_THRESHOLD } from '../lib/constants';
import './GuidePage.css';

interface FAQItem {
  q: string;
  a: string;
}

const FAQS: FAQItem[] = [
  {
    q: 'Why does TruthGuard withhold an answer instead of just guessing?',
    a: 'In academic regulations (such as attendance requirements, passing marks, or arrear maximums), a small error can cause a student to be barred from examinations or repeat an entire semester. When evidence is lacking or contradictory, withholding with a clear explanation prevents real-world academic harm.',
  },
  {
    q: 'What is the difference between an Unsupported claim and a Contradicted claim?',
    a: 'An Unsupported claim is one where the Sri Sairam 2024 regulations neither confirm nor deny the statement (lack of evidence). A Contradicted claim directly violates what is written in the official text (e.g., claiming 60% attendance is permitted when Clause 7.3 strictly forbids it).',
  },
  {
    q: 'What makes a claim "Critical"?',
    a: 'Claims involving quantitative constraints, deadlines, monetary penalties, or pass/fail thresholds are tagged as Critical. Critical claims carry double weight (w = 2.0) in the risk formula and any contradiction immediately withholds the entire answer.',
  },
  {
    q: 'Can faculty and examiners inspect the exact regulation citation?',
    a: 'Yes. Every verified claim includes a clickable citation to the exact section heading and page number in the Sri Sairam Autonomous Regulations 2024 PDF. Clicking "Jump to Passage" scrolls directly to the matching excerpt.',
  },
  {
    q: 'Where do the evaluation metrics come from?',
    a: 'All metrics shown in the Evaluation Dashboard are computed directly against the 30-question Gold Benchmark dataset curated from the official regulations, partitioned into stratified Dev and Test splits.',
  },
];

export function GuidePage() {
  const [activeTab, setActiveTab] = useState<'LABELS' | 'DECISIONS' | 'FORMULA' | 'PIPELINE' | 'FAQS'>('LABELS');
  const [openFaqIndex, setOpenFaqIndex] = useState<number | null>(0);

  return (
    <>
      <TopBar
        title="Guide & Methodology"
        subtitle="Plain-English documentation of TruthGuard AI verification standards and formulas"
      />

      <div className="app-content">
        <div className="content-container guide-container">

          {/* 1. Header Overview Banner */}
          <div className="guide-hero animate-fade-in-up">
            <div className="hero-content">
              <span className="hero-tag">System Reference</span>
              <h2 className="hero-title">How TruthGuard AI Verifies Academic Regulations</h2>
              <p className="hero-description">
                Unlike standard generative chatbots that answer on faith, TruthGuard AI enforces a formal evidence-verification contract against the <strong>Sri Sairam Autonomous Academic Regulations 2024</strong>. Answers are verified at the atomic claim level before release.
              </p>
            </div>
            <div className="guide-quick-pills">
              <button
                className={`guide-tab-btn ${activeTab === 'LABELS' ? 'active' : ''}`}
                onClick={() => setActiveTab('LABELS')}
              >
                <Zap size={14} />
                <span>Claim Labels</span>
              </button>
              <button
                className={`guide-tab-btn ${activeTab === 'DECISIONS' ? 'active' : ''}`}
                onClick={() => setActiveTab('DECISIONS')}
              >
                <Scale size={14} />
                <span>Decision Gating</span>
              </button>
              <button
                className={`guide-tab-btn ${activeTab === 'FORMULA' ? 'active' : ''}`}
                onClick={() => setActiveTab('FORMULA')}
              >
                <Calculator size={14} />
                <span>Risk Math</span>
              </button>
              <button
                className={`guide-tab-btn ${activeTab === 'PIPELINE' ? 'active' : ''}`}
                onClick={() => setActiveTab('PIPELINE')}
              >
                <Cpu size={14} />
                <span>5-Stage Pipeline</span>
              </button>
              <button
                className={`guide-tab-btn ${activeTab === 'FAQS' ? 'active' : ''}`}
                onClick={() => setActiveTab('FAQS')}
              >
                <HelpCircle size={14} />
                <span>FAQ</span>
              </button>
            </div>
          </div>

          {/* ── SECTION 1: CLAIM LABELS ── */}
          {(activeTab === 'LABELS' || activeTab === 'ALL' as any) && (
            <div className="guide-section animate-fade-in">
              <div className="section-header">
                <Zap size={18} className="text-accent" />
                <h3>1. Atomic Claim Verification Labels</h3>
              </div>
              <p className="section-lead">
                Every generated response is decomposed into standalone factual statements. The Natural Language Inference (NLI) model classifies each statement into one of three strict categories:
              </p>

              <div className="labels-grid">

                {/* Verified Card */}
                <div className="label-card label-card-verified">
                  <div className="label-card-top">
                    <div className="label-badge-wrap">
                      <CheckCircle2 size={18} className="text-success" />
                      <StatusBadge status="Verified" size="md" />
                    </div>
                    <span className="label-condition">Entailment E<sub>i</sub> &ge; 70%</span>
                  </div>
                  <h4 className="label-name">Verified (Directly Grounded)</h4>
                  <p className="label-desc">
                    The statement is explicitly supported by the retrieved regulation passage. The text confirms the policy with high semantic certainty.
                  </p>
                  <div className="label-example-box">
                    <span className="example-title">Regulation Example:</span>
                    <p className="example-quote">
                      "A student who secures 85% attendance is permitted to appear for end-semester examinations."
                    </p>
                    <span className="example-cite">Matches Clause 7.1 (Page 20)</span>
                  </div>
                </div>

                {/* Unsupported Card */}
                <div className="label-card label-card-unsupported">
                  <div className="label-card-top">
                    <div className="label-badge-wrap">
                      <AlertTriangle size={18} className="text-warning" />
                      <StatusBadge status="Unsupported" size="md" />
                    </div>
                    <span className="label-condition">E<sub>i</sub> &lt; 70% &amp; K<sub>i</sub> &lt; 60%</span>
                  </div>
                  <h4 className="label-name">Unsupported (No Policy Evidence)</h4>
                  <p className="label-desc">
                    The statement is neither confirmed nor contradicted by the official document. The regulations simply contain no clause covering this claim.
                  </p>
                  <div className="label-example-box">
                    <span className="example-title">Regulation Example:</span>
                    <p className="example-quote">
                      "Hostel students receive free transportation to Chennai Central on weekends."
                    </p>
                    <span className="example-cite">No supporting clause in academic regulations</span>
                  </div>
                </div>

                {/* Contradicted Card */}
                <div className="label-card label-card-contradicted">
                  <div className="label-card-top">
                    <div className="label-badge-wrap">
                      <XCircle size={18} className="text-danger" />
                      <StatusBadge status="Contradicted" size="md" />
                    </div>
                    <span className="label-condition">Contradiction K<sub>i</sub> &ge; 60%</span>
                  </div>
                  <h4 className="label-name">Contradicted (Direct Policy Conflict)</h4>
                  <p className="label-desc">
                    The statement directly violates or asserts the opposite of the official rule. This represents a severe hallucination risk that triggers withholding.
                  </p>
                  <div className="label-example-box">
                    <span className="example-title">Regulation Example:</span>
                    <p className="example-quote">
                      "Students with 60% attendance can write semester exams with mentor approval."
                    </p>
                    <span className="example-cite">Violates Clause 7.3 (less than 65% strictly prohibited)</span>
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* ── SECTION 2: DECISION GATING ── */}
          {(activeTab === 'DECISIONS' || activeTab === 'ALL' as any) && (
            <div className="guide-section animate-fade-in">
              <div className="section-header">
                <Scale size={18} className="text-accent" />
                <h3>2. Calibrated Decision Gating</h3>
              </div>
              <p className="section-lead">
                TruthGuard AI evaluates 3 mandatory safety criteria before deciding whether to <strong>RELEASE</strong> or <strong>WITHHOLD</strong> an answer:
              </p>

              <div className="decisions-container">

                {/* Checklist Card */}
                <Card title="The 3 Verification Criteria" icon={<ShieldCheck size={16} />}>
                  <div className="criteria-list">
                    <div className="criteria-item">
                      <div className="criteria-icon pass-icon">
                        <CheckCircle2 size={18} />
                      </div>
                      <div className="criteria-text">
                        <strong>Criterion 1: Zero Contradictions</strong>
                        <p>Contradiction count must equal 0. If even one claim contradicts the regulations, the response is withheld immediately to prevent misguidance.</p>
                      </div>
                    </div>

                    <div className="criteria-item">
                      <div className="criteria-icon pass-icon">
                        <CheckCircle2 size={18} />
                      </div>
                      <div className="criteria-text">
                        <strong>Criterion 2: Calibrated Risk Score &le; {(RISK_THRESHOLD * 100).toFixed(0)}%</strong>
                        <p>Weighted risk of unsupported claims must remain below the calibrated threshold &tau; = {RISK_THRESHOLD}. If risk exceeds 25%, the answer is withheld.</p>
                      </div>
                    </div>

                    <div className="criteria-item">
                      <div className="criteria-icon pass-icon">
                        <CheckCircle2 size={18} />
                      </div>
                      <div className="criteria-text">
                        <strong>Criterion 3: Minimum Evidence Floor</strong>
                        <p>At least one relevant regulation passage must match with a hybrid retrieval score &ge; 0.30. Out-of-domain questions trigger an automatic NO_EVIDENCE withhold.</p>
                      </div>
                    </div>
                  </div>
                </Card>

                {/* Reason Codes Card */}
                <Card title="Official Decision Reason Codes" icon={<FileText size={16} />}>
                  <div className="reasons-table-wrap">
                    <table className="reasons-table">
                      <thead>
                        <tr>
                          <th>Reason Code</th>
                          <th>Outcome</th>
                          <th>Condition</th>
                          <th>User-Facing Explanation</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td><code>NONE</code></td>
                          <td><span className="badge-pass">RELEASED</span></td>
                          <td>Risk &le; 0.25 &amp; 0 contradictions</td>
                          <td>"Verified and cross-checked against Sri Sairam 2024 Regulations."</td>
                        </tr>
                        <tr>
                          <td><code>NO_EVIDENCE</code></td>
                          <td><span className="badge-withheld">WITHHELD</span></td>
                          <td>Retrieved score &lt; 0.30 floor</td>
                          <td>"No relevant policy exists in the regulations corpus for this query."</td>
                        </tr>
                        <tr>
                          <td><code>CRITICAL_CONTRADICTION</code></td>
                          <td><span className="badge-withheld">WITHHELD</span></td>
                          <td>&ge; 1 contradicted claim</td>
                          <td>"Draft answer directly contradicts official regulation clause."</td>
                        </tr>
                        <tr>
                          <td><code>RISK_ABOVE_THRESHOLD</code></td>
                          <td><span className="badge-withheld">WITHHELD</span></td>
                          <td>Total risk &gt; 0.25 ceiling</td>
                          <td>"Calibrated uncertainty exceeds safe release tolerance threshold."</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </Card>

              </div>
            </div>
          )}

          {/* ── SECTION 3: RISK MATH & FORMULA ── */}
          {(activeTab === 'FORMULA' || activeTab === 'ALL' as any) && (
            <div className="guide-section animate-fade-in">
              <div className="section-header">
                <Calculator size={18} className="text-accent" />
                <h3>3. Mathematical Formulation (Examiner Reference)</h3>
              </div>
              <p className="section-lead">
                TruthGuard replaces subjective heuristics with a rigorous, reproducible risk scoring function:
              </p>

              <div className="formula-cards-grid">

                {/* Formula 1 */}
                <Card title="Per-Claim Penalty Function s(y_i)" icon={<Sliders size={16} />}>
                  <div className="math-display-box">
                    <code className="math-code">
                      s(y_i) = 0.00 &nbsp;if Verified<br />
                      s(y_i) = &alpha; = 0.50 &nbsp;if Unsupported<br />
                      s(y_i) = 1.00 &nbsp;if Contradicted
                    </code>
                  </div>
                  <p className="formula-explanation">
                    Verified claims add zero penalty. Unsupported statements carry a calibrated penalty &alpha; = 0.50, and contradictions are penalized at maximum severity (1.00).
                  </p>
                </Card>

                {/* Formula 2 */}
                <Card title="Weighted Answer Risk Score R" icon={<Calculator size={16} />}>
                  <div className="math-display-box">
                    <code className="math-code">
                      R(a, P) = &Sigma;(w_i &middot; s(y_i)) / &Sigma;(w_i)
                    </code>
                  </div>
                  <p className="formula-explanation">
                    Total risk is the weighted average penalty of all atomic claims in the answer. Critical statements (deadlines, percentages, grade cutoffs) are weighted at w = 2.0.
                  </p>
                </Card>

                {/* Parameters Table */}
                <Card title="Calibrated Hyperparameters" icon={<Sliders size={16} />}>
                  <div className="params-list">
                    <div className="param-row">
                      <span className="param-k">&tau; (Risk Ceiling):</span>
                      <strong className="param-v">0.25 (25.0%)</strong>
                      <span className="param-desc">Optimal abstention ceiling discovered on DEV split</span>
                    </div>
                    <div className="param-row">
                      <span className="param-k">&alpha; (Unsupported Penalty):</span>
                      <strong className="param-v">0.50</strong>
                      <span className="param-desc">Penalty weight assigned to ungrounded claims</span>
                    </div>
                    <div className="param-row">
                      <span className="param-k">&theta;<sub>e</sub> (Entailment Floor):</span>
                      <strong className="param-v">0.70 (70.0%)</strong>
                      <span className="param-desc">DeBERTa-v3 confidence required for Verified badge</span>
                    </div>
                    <div className="param-row">
                      <span className="param-k">&theta;<sub>c</sub> (Contradiction Floor):</span>
                      <strong className="param-v">0.60 (60.0%)</strong>
                      <span className="param-desc">Confidence threshold for immediate Contradicted flag</span>
                    </div>
                  </div>
                </Card>

              </div>
            </div>
          )}

          {/* ── SECTION 4: 5-STAGE PIPELINE ── */}
          {(activeTab === 'PIPELINE' || activeTab === 'ALL' as any) && (
            <div className="guide-section animate-fade-in">
              <div className="section-header">
                <Cpu size={18} className="text-accent" />
                <h3>4. End-to-End 5-Stage Architecture</h3>
              </div>
              <p className="section-lead">
                Every query passes through a sequential multi-agent LangGraph workflow:
              </p>

              <div className="pipeline-flow-grid">

                <div className="pipeline-flow-step">
                  <div className="flow-step-num">1</div>
                  <div className="flow-step-content">
                    <h4>Hybrid Passage Retrieval</h4>
                    <span className="flow-tech">BAAI/bge-small-en-v1.5 + BM25 + RRF</span>
                    <p>
                      Queries the vectorized Chroma database and lexical BM25 index. Combines rankings using Reciprocal Rank Fusion ($k=60$) to return top-5 regulation passages with neighbour context.
                    </p>
                  </div>
                </div>

                <div className="pipeline-flow-step">
                  <div className="flow-step-num">2</div>
                  <div className="flow-step-content">
                    <h4>Answer Generation</h4>
                    <span className="flow-tech">Google Gemini with Grounded Prompt</span>
                    <p>
                      Synthesizes a structured draft answer strictly conditioned on the retrieved regulation context, citing clause numbers and policies.
                    </p>
                  </div>
                </div>

                <div className="pipeline-flow-step">
                  <div className="flow-step-num">3</div>
                  <div className="flow-step-content">
                    <h4>Atomic Claim Decomposition</h4>
                    <span className="flow-tech">Claim Extractor Agent</span>
                    <p>
                      Decomposes complex paragraphs into atomic, testable propositions. Identifies claim typology (condition, deadline, exception, penalty) and marks critical constraints.
                    </p>
                  </div>
                </div>

                <div className="pipeline-flow-step">
                  <div className="flow-step-num">4</div>
                  <div className="flow-step-content">
                    <h4>NLI Claim Verification</h4>
                    <span className="flow-tech">DeBERTa-v3 on Apple Silicon MPS</span>
                    <p>
                      Computes cross-encoder entailment, neutral, and contradiction probabilities ($E_i, N_i, K_i$) for each claim against the retrieved passages.
                    </p>
                  </div>
                </div>

                <div className="pipeline-flow-step">
                  <div className="flow-step-num">5</div>
                  <div className="flow-step-content">
                    <h4>Risk Calibration &amp; Decision</h4>
                    <span className="flow-tech">Risk Decision Agent</span>
                    <p>
                      Calculates total risk score $R$. Gating logic releases audited answer if safe, or withholds with reason explanation if risk exceeds $\tau = 0.25$ or contradiction is found.
                    </p>
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* ── SECTION 5: FREQUENTLY ASKED QUESTIONS ── */}
          {(activeTab === 'FAQS' || activeTab === 'ALL' as any) && (
            <div className="guide-section animate-fade-in">
              <div className="section-header">
                <HelpCircle size={18} className="text-accent" />
                <h3>5. Frequently Asked Questions (FAQ)</h3>
              </div>
              <p className="section-lead">
                Common questions from students, faculty coordinators, and examiners regarding system behavior:
              </p>

              <div className="faqs-list">
                {FAQS.map((faq, idx) => {
                  const isOpen = openFaqIndex === idx;
                  return (
                    <div key={idx} className="faq-card">
                      <div
                        className="faq-question"
                        onClick={() => setOpenFaqIndex(isOpen ? null : idx)}
                      >
                        <span className="faq-q-text">{faq.q}</span>
                        <button className="faq-toggle-btn">
                          {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </button>
                      </div>
                      {isOpen && (
                        <div className="faq-answer animate-fade-in">
                          <p>{faq.a}</p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

        </div>
      </div>
    </>
  );
}
