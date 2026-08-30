import React from 'react';

interface ConfidenceBadgeProps {
  confidence: "low" | "medium" | "high";
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
  const getConfidencePercentage = (level: "low" | "medium" | "high") => {
    if (level === 'high') return 100;
    if (level === 'medium') return 66;
    return 33;
  };

  const percentage = getConfidencePercentage(confidence);

  return (
    <div className="confidence-badge">
      {showLabel && <span>Confidence: </span>}
      <span>{percentage}%</span>
    </div>
  );
};
