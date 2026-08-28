import { useState } from 'react'
import './App.css'
import { JurisdictionToggle, ChatInterface, ProviderConsent } from './components'

function App() {
  const [jurisdiction, setJurisdiction] = useState<'india' | 'international' | 'comparative'>('india')
  const [provider, setProvider] = useState<string>('self_hosted')
  const [hasProviderConsent, setHasProviderConsent] = useState(false)

  const handleSendMessage = async (message: string, selectedJurisdiction: string) => {
    // Placeholder - in production, this would call the API
    console.log('Sending message:', message, 'Jurisdiction:', selectedJurisdiction)
    
    // Simulate API response
    return {
      answer: 'This is a placeholder response. The actual implementation will connect to the orchestrator service.',
      citations: [
        {
          source_id: 'Patents Act 1970',
          section: '3',
          article: '3(p)',
          version_hash: 'abc123def456',
          confidence: 0.85
        }
      ],
      confidence: 0.82
    }
  }

  const handleProviderConsent = (consented: boolean, selectedProvider: string) => {
    setHasProviderConsented(consented)
    if (consented) {
      setProvider(selectedProvider)
    } else {
      setProvider('self_hosted')
    }
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>IP-SAKTI Sahayak</h1>
        <p>Multilingual, RAG-based AI assistant for Ayurveda IPR & regulatory guidance</p>
        <div className="disclaimer">
          <strong>Disclaimer:</strong> This system provides information only, not legal advice. 
          For legal matters, please consult with a qualified legal professional.
        </div>
      </header>
      <main className="App-main">
        <div className="controls-section">
          <JurisdictionToggle
            jurisdiction={jurisdiction}
            onJurisdictionChange={setJurisdiction}
          />
          <ProviderConsent
            onConsentChange={handleProviderConsent}
            provider={provider}
            currentProvider={provider}
          />
        </div>
        <ChatInterface
          onSendMessage={handleSendMessage}
          jurisdiction={jurisdiction}
        />
      </main>
    </div>
  )
}

export default App
