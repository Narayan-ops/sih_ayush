import React from 'react';

interface Citation {
  source_id: string;
  section: string;
  article: string;
  confidence: number;
}

interface CitationDisplayProps {
  citations: Citation[];
}

/**
 * Citation Display Component
 * 
 * Per AGENTS.md #1: Every answer must have citable source support
 * Displays citations with source_id, section/article
 */
export const CitationDisplay: React.FC<CitationDisplayProps> = ({ citations }) => {
  if (!citations || citations.length === 0) {
    return null;
  }

  return (
    <div className="citations">
      <strong>Sources:</strong>
      <ul>
        {citations.map((citation, idx) => (
          <li key={idx} className="citation-item">
            [{citation.source_id || 'Unknown'}{citation.section ? `, ${citation.section}` : ''}{citation.article ? `, ${citation.article}` : ''}]
            {citation.confidence !== undefined && (
              <span className="citation-confidence">
                (Confidence: {(citation.confidence * 100).toFixed(0)}%)
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
};
