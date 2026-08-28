import React, { useState } from 'react';

interface ProviderConsentProps {
  onConsentChange: (consented: boolean, provider: string) => void;
  provider: string;
  currentProvider: string;
}

/**
 * Provider Consent Component
 * 
 * Per ADR-001: External providers are opt-in only, per-session, with explicit logged consent
 * Per DPDP Act: Consent management for data processing
 */
export const ProviderConsent: React.FC<ProviderConsentProps> = ({
  onConsentChange,
  provider,
  currentProvider
}) => {
  const [hasConsented, setHasConsented] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const handleConsent = (consented: boolean) => {
    setHasConsented(consented);
    onConsentChange(consented, provider);
  };

  const isSelfHosted = provider === 'self_hosted';

  return (
    <div className="provider-consent">
      <div className="consent-header">
        <h4>AI Model Provider</h4>
        <button
          className="toggle-details"
          onClick={() => setShowDetails(!showDetails)}
          aria-expanded={showDetails}
        >
          {showDetails ? 'Hide Details' : 'Show Details'}
        </button>
      </div>

      <div className="provider-selection">
        <div className="provider-option">
          <input
            type="radio"
            id="self-hosted"
            name="provider"
            value="self_hosted"
            checked={currentProvider === 'self_hosted'}
            onChange={() => {}}
            disabled
          />
          <label htmlFor="self-hosted">
            <strong>Self-Hosted (Default)</strong>
            <span className="provider-description">
              Llama 3.1 8B / Mistral-NeMo 12B on GoI infrastructure
            </span>
            <span className="provider-badge self-hosted">Recommended</span>
          </label>
        </div>

        <div className="provider-option">
          <input
            type="radio"
            id="openai"
            name="provider"
            value="openai"
            checked={currentProvider === 'openai'}
            onChange={() => {}}
            disabled={!hasConsented}
          />
          <label htmlFor="openai">
            <strong>OpenAI GPT-4o</strong>
            <span className="provider-description">
              External provider - requires consent
            </span>
            <span className="provider-badge external">External</span>
          </label>
        </div>

        <div className="provider-option">
          <input
            type="radio"
            id="anthropic"
            name="provider"
            value="anthropic"
            checked={currentProvider === 'anthropic'}
            onChange={() => {}}
            disabled={!hasConsented}
          />
          <label htmlFor="anthropic">
            <strong>Anthropic Claude</strong>
            <span className="provider-description">
              External provider - requires consent
            </span>
            <span className="provider-badge external">External</span>
          </label>
        </div>
      </div>

      {!isSelfHosted && (
        <div className="consent-form">
          <div className="consent-checkbox">
            <input
              type="checkbox"
              id="external-consent"
              checked={hasConsented}
              onChange={(e) => handleConsent(e.target.checked)}
            />
            <label htmlFor="external-consent">
              <strong>I consent to using external AI providers</strong>
              <p className="consent-notice">
                By checking this box, I understand that:
              </p>
              <ul className="consent-details">
                <li>
                  My query will be processed by an external AI provider (
                  {currentProvider === 'openai' ? 'OpenAI' : 'Anthropic'})
                </li>
                <li>
                  This is a one-time consent for this session only
                </li>
                <li>
                  This consent will be logged for audit purposes per DPDP Act requirements
                </li>
                <li>
                  The self-hosted model is recommended for data sovereignty
                </li>
              </ul>
            </label>
          </div>
        </div>
      )}

      {showDetails && (
        <div className="provider-details">
          <h5>Data Sovereignty Information</h5>
          <p>
            <strong>Self-Hosted Model:</strong> Runs on GoI empanelled cloud infrastructure 
            (MeghRaj/NIC). No data leaves India. Recommended for sensitive formulation queries.
          </p>
          <p>
            <strong>External Providers:</strong> Data may be processed outside India. 
            Requires explicit consent per ADR-001 and DPDP Act. Consent is logged and 
            auditable. Use only if self-hosted model performance is insufficient.
          </p>
          <p className="data-residency-notice">
            <em>Per ARCHITECTURE.md §10: All default infrastructure runs on GoI empanelled cloud.</em>
          </p>
        </div>
      )}
    </div>
  );
};
