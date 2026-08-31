import React, { useState, useRef, useEffect } from 'react';
import { CitationDisplay, ConfidenceBadge } from './index';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: any[];
  confidence?: "low" | "medium" | "high";
  formulation_class?: string | null;
  requires_escalation?: boolean;
  timestamp: Date;
}

interface ChatInterfaceProps {
  onSendMessage: (message: string, jurisdiction: string) => Promise<any>;
  jurisdiction: string;
}

/**
 * Chat Interface Component
 * 
 * Displays chat messages with citations and confidence indicators
 * Per AGENTS.md #1: Every answer must have citable source support
 */
export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  onSendMessage,
  jurisdiction
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response: any = await onSendMessage(input, jurisdiction);
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response?.message?.content || response?.answer || response?.content || JSON.stringify(response) || '',
        citations: response?.citations,
        confidence: response?.confidence,
        formulation_class: response?.formulation_class,
        requires_escalation: response?.requires_escalation,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, there was an error processing your request. Please try again.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {messages.length === 0 && (
          <div className="welcome-message">
            <h2>Welcome to IP-SAKTI Sahayak</h2>
            <p>
              Ask questions about Ayurveda intellectual property and regulatory guidance.
              <br />
              Jurisdiction: <strong>{jurisdiction.toUpperCase()}</strong>
            </p>
          </div>
        )}
        
        {messages.map((message) => (
          <div
            key={message.id}
            className={`message ${message.role}`}
          >
            <div className="message-content">
              <p>{message.content}</p>
              
              {message.role === 'assistant' && message.citations && (
                <CitationDisplay citations={message.citations} />
              )}
              
              {message.role === 'assistant' && message.confidence !== undefined && (
                <ConfidenceBadge confidence={message.confidence} />
              )}
            </div>
            <div className="message-timestamp">
              {message.timestamp.toLocaleTimeString()}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="message assistant loading">
            <div className="loading-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      <div className="input-container">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your question about Ayurveda IP..."
          rows={3}
          disabled={isLoading}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          className="send-button"
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
};
