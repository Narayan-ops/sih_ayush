import React from 'react';

interface ConfidenceBadgeProps {
  confidence: number;
  showLabel?: boolean;
}

/**
 * Confidence Badge Component
 * 
 * Displays confidence score with color coding
 * Per ARCHITECTURE.md: Safe abstention when confidence is insufficient
 */
export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  confidence,
  showLabel = true
}) => {
  const getConfidenceInfo = (score: number) => {
    if (score >= 0.8) return { level: 'High', color: 'green' };
    if (score >= 0.6) return { level: 'Medium', color: 'yellow' };
    if (score >= 0.4) return { level: 'Low', color: 'orange' };
    return { level: 'Very Low', color: 'red' };
  };

  const { level, color } = getConfidenceInfo(confidence);

  return (
    <div className={`confidence-badge confidence-${color}`}>
      {showLabel && <span className="confidence-label">Confidence:</span>}
      <span className="confidence-value">{(confidence * 100).toFixed(0)}%</span>
      <span className="confidence-level">({level})</span>
    </div>
  );
};
