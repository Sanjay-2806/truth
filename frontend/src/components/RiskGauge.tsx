import { RISK_THRESHOLD } from '../lib/constants';
import './RiskGauge.css';

interface RiskGaugeProps {
  value: number;           // 0–1
  size?: number;           // px, default 80
  showLabel?: boolean;
}

export function RiskGauge({ value, size = 80, showLabel = true }: RiskGaugeProps) {
  const clampedValue = Math.max(0, Math.min(1, value));
  const percentage = clampedValue * 100;

  // Arc calculations (semi-circle, 180 degrees)
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = Math.PI * radius;   // half-circle
  const dashOffset = circumference - (clampedValue * circumference);
  const thresholdOffset = circumference - (RISK_THRESHOLD * circumference);

  // Color based on risk level
  const getColor = () => {
    if (clampedValue <= RISK_THRESHOLD * 0.6) return 'var(--color-verified)';
    if (clampedValue <= RISK_THRESHOLD) return 'var(--color-unsupported)';
    return 'var(--color-contradicted)';
  };

  return (
    <div className="risk-gauge" style={{ width: size, height: size / 2 + 20 }}>
      <svg
        width={size}
        height={size / 2 + strokeWidth}
        viewBox={`0 0 ${size} ${size / 2 + strokeWidth}`}
      >
        {/* Background arc */}
        <path
          d={`M ${strokeWidth / 2} ${size / 2}
              A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
          fill="none"
          stroke="var(--border)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />

        {/* Value arc */}
        <path
          d={`M ${strokeWidth / 2} ${size / 2}
              A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
          fill="none"
          stroke={getColor()}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          className="gauge-value-arc"
        />

        {/* Threshold marker */}
        <path
          d={`M ${strokeWidth / 2} ${size / 2}
              A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
          fill="none"
          stroke="transparent"
          strokeWidth={strokeWidth + 6}
          strokeDasharray={`2 ${circumference - 2}`}
          strokeDashoffset={thresholdOffset}
          strokeLinecap="butt"
          opacity="0.6"
        />
      </svg>

      {showLabel && (
        <div className="gauge-label">
          <span className="gauge-value" style={{ color: getColor() }}>
            {percentage.toFixed(0)}%
          </span>
          <span className="gauge-caption">Risk</span>
        </div>
      )}
    </div>
  );
}
