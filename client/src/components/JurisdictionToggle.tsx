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
          className={`toggle-button ${jurisdiction === 'comparative' ? 'active' : ''}`}
          onClick={() => onJurisdictionChange('comparative')}
          aria-label="Comparative mode (both jurisdictions)"
        >
          Comparative
        </button>
      </div>
      {jurisdiction === 'comparative' && (
        <div className="comparative-notice">
          <p>
            <strong>Comparative Mode:</strong> Results from both India and International 
            jurisdictions will be displayed side-by-side for comparison.
          </p>
        </div>
      )}
    </div>
  );
};
