import React from 'react';

interface JurisdictionToggleProps {
  jurisdiction: 'india' | 'international' | 'comparative';
  onJurisdictionChange: (jurisdiction: 'india' | 'international' | 'comparative') => void;
}

/**
 * Jurisdiction Toggle Component
 * 
 * Per ADR-003: Jurisdiction separation is structural, not cosmetic
 * Per ARCHITECTURE.md: Comparative mode is explicit opt-in only, rendered as two columns
 */
export const JurisdictionToggle: React.FC<JurisdictionToggleProps> = ({
  jurisdiction,
  onJurisdictionChange
}) => {
  return (
    <div className="jurisdiction-toggle">
      <label className="toggle-label">
        Select Jurisdiction:
      </label>
      <div className="toggle-buttons">
        <button
          className={`toggle-button ${jurisdiction === 'india' ? 'active' : ''}`}
          onClick={() => onJurisdictionChange('india')}
          aria-label="India jurisdiction"
        >
          India
        </button>
        <button
          className={`toggle-button ${jurisdiction === 'international' ? 'active' : ''}`}
          onClick={() => onJurisdictionChange('international')}
          aria-label="International jurisdiction"
        >
          International
        </button>
        <button
          className="toggle-button"
          disabled
          title="Comparative answers require two independently grounded answer sets; this view is not enabled yet."
          aria-label="Comparative mode is not yet available"
        >
          Comparative (coming soon)
        </button>
      </div>
    </div>
  );
};
