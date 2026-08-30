import React from 'react';

/**
 * About Page
 * Information about IP-SAKTI Sahayak
 */
export const About: React.FC = () => {
  return (
    <div className="about-page">
      <h1>About IP-SAKTI Sahayak</h1>
      
      <section>
        <h2>Overview</h2>
        <p>
          IP-SAKTI Sahayak is a multilingual, RAG-based AI assistant for Ayurveda 
          intellectual property and regulatory guidance. It is developed for the 
          Ministry of AYUSH / All India Institute of Ayurveda (AIIA).
        </p>
      </section>

      <section>
        <h2>Key Features</h2>
        <ul>
          <li>Citation-based answers with source attribution</li>
          <li>Jurisdiction-separated retrieval (India and International)</li>
          <li>Deterministic formulation classification</li>
          <li>Confidence scoring with safe abstention</li>
          <li>Data sovereignty through self-hosted services</li>
        </ul>
      </section>

      <section>
        <h2>Important Disclaimer</h2>
        <div className="disclaimer-box">
          <strong>This system provides information only, not legal advice.</strong>
          <p>
            For legal matters regarding intellectual property, patent applications, 
            or regulatory compliance, please consult with a qualified legal professional 
            or the All India Institute of Ayurveda.
          </p>
        </div>
      </section>

      <section>
        <h2>Data Sovereignty</h2>
        <p>
          This system is designed to operate on GoI-empanelled cloud infrastructure 
          (MeghRaj/NIC) to ensure data sovereignty. Self-hosted models are the default 
          for all processing. External providers are opt-in only with explicit consent.
        </p>
      </section>

      <section>
        <h2>Phase Information</h2>
        <p>
          This is Phase 1 MVP of the 18-week production implementation. Future phases 
          will include knowledge graph capabilities, paid-source connectors, and 
          multilingual voice support.
        </p>
      </section>
    </div>
  );
};
