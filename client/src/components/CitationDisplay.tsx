import React from 'react';

interface Citation {
  source_id: string;
  section: string;
  article: string;
  version_hash: string;
  confidence: number;
  span_match?: string;
}

interface CitationDisplayProps {
  citations: Citation[];
}

/**
 * Citation Display Component
 * 
 * Per AGENTS.md #1: Every answer must have citable source support
 * Displays citations with source_id, section/article, version_hash
 */
export const CitationDisplay: React.FC<CitationDisplayProps> = ({ citations }) => {
  if (!citations || citations.length === 0) {
    return (
      <div className="citation-display no-citations">
        <p>No citations available</p>
      </div>
    );
  }

  return (
    <div className="citation-display">
      <h4>Sources</h4>
      <ul className="citation-list">
        {citations.map((citation, idx) => (
          <li key={idx} className="citation-item">
            <div className="citation-main">
              <span className="citation-source">{citation.source_id}</span>
              <span className="citation-section">
                Section {citation.section}, Article {citation.article}
              </span>
            </div>
            <div className="citation-details">
              <span className="citation-confidence">
                Confidence: {(citation.confidence * 100).toFixed(0)}%
              </span>
              <span className="citation-version">
                Version: {citation.version_hash.substring(0, 8)}...
              </span>
            </div>
            {citation.span_match && (
              <div className="citation-span">
                <em>"{citation.span_match}"</em>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
};
