import { useState } from 'react'
import './App.css'
import { JurisdictionToggle, ChatInterface, ProviderConsent } from './components'
import { apiService } from './services/api'

function App() {
  const [jurisdiction, setJurisdiction] = useState<'india' | 'international' | 'comparative'>('india')
  const [provider, setProvider] = useState<string>('self_hosted')

  const handleSendMessage = async (message: string, selectedJurisdiction: string) => {
    try {
      const response = await apiService.sendMessage({
        message,
        jurisdiction: selectedJurisdiction as 'india' | 'international' | 'comparative'
      })
      return response
    } catch (error) {
      console.error('Error sending message:', error)
      throw error
    }
  }

  const handleProviderConsent = (consented: boolean, selectedProvider: string) => {
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
