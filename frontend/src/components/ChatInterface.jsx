import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import DecisionRecord from './DecisionRecord';
import './ChatInterface.css';

const MODES = [
  { value: 'mini', label: 'Mini — answers + synthesis' },
  { value: 'review', label: 'Review — multi-model critique' },
  { value: 'full', label: 'Full — answers + ranking + synthesis' },
  { value: 'extract', label: 'Extract — decision record' },
];

const PRESETS = [
  { value: 'cheap', label: 'Cheap' },
  { value: 'balanced', label: 'Balanced' },
  { value: 'premium', label: 'Premium' },
];

// Per-mode labels so a single set of components renders every mode.
const MODE_LABELS = {
  mini: { stage1: 'Individual Responses', stage3: 'Final Council Answer' },
  full: { stage1: 'Stage 1: Individual Responses', stage3: 'Stage 3: Final Council Answer' },
  review: { stage1: 'Critiques', stage3: 'Consolidated Review' },
  extract: { stage1: '', stage3: '' },
};

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
}) {
  const [input, setInput] = useState('');
  const [mode, setMode] = useState('mini');
  const [preset, setPreset] = useState('balanced');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input, mode, preset);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="empty-state">
          <h2>Welcome to LLM Council</h2>
          <p>Create a new conversation to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {conversation.messages.length === 0 ? (
          <div className="empty-state">
            <h2>Start a conversation</h2>
            <p>Ask a question to consult the LLM Council</p>
          </div>
        ) : (
          conversation.messages.map((msg, index) => (
            <div key={index} className="message-group">
              {msg.role === 'user' ? (
                <div className="user-message">
                  <div className="message-label">You</div>
                  <div className="message-content">
                    <div className="markdown-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                (() => {
                  const msgMode = msg.mode || 'full';
                  const labels = MODE_LABELS[msgMode] || MODE_LABELS.full;
                  const isReview = msgMode === 'review';
                  return (
                    <div className="assistant-message">
                      <div className="message-label">
                        LLM Council{msg.mode ? ` · ${msgMode}` : ''}
                      </div>

                      {/* Extract mode: decision record only */}
                      {msg.loading?.extract && (
                        <div className="stage-loading">
                          <div className="spinner"></div>
                          <span>Extracting decision record...</span>
                        </div>
                      )}
                      {msg.decisionRecord && (
                        <DecisionRecord
                          record={msg.decisionRecord}
                          markdown={msg.decisionMarkdown}
                        />
                      )}

                      {/* Stage 1 (answers) / Critiques (review) */}
                      {msg.loading?.stage1 && (
                        <div className="stage-loading">
                          <div className="spinner"></div>
                          <span>
                            {isReview
                              ? 'Collecting critiques...'
                              : 'Collecting individual responses...'}
                          </span>
                        </div>
                      )}
                      {msg.stage1 && (
                        <Stage1 responses={msg.stage1} title={labels.stage1} />
                      )}

                      {/* Stage 2 (ranking — full mode only) */}
                      {msg.loading?.stage2 && (
                        <div className="stage-loading">
                          <div className="spinner"></div>
                          <span>Running peer rankings...</span>
                        </div>
                      )}
                      {msg.stage2 && msg.stage2.length > 0 && (
                        <Stage2
                          rankings={msg.stage2}
                          labelToModel={msg.metadata?.label_to_model}
                          aggregateRankings={msg.metadata?.aggregate_rankings}
                        />
                      )}

                      {/* Stage 3 (synthesis) */}
                      {msg.loading?.stage3 && (
                        <div className="stage-loading">
                          <div className="spinner"></div>
                          <span>
                            {isReview
                              ? 'Synthesizing consolidated review...'
                              : 'Synthesizing final answer...'}
                          </span>
                        </div>
                      )}
                      {msg.stage3 && msg.stage3.response && (
                        <Stage3 finalResponse={msg.stage3} title={labels.stage3} />
                      )}
                    </div>
                  );
                })()
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Consulting the council...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {conversation.messages.length === 0 && (
        <form className="input-form" onSubmit={handleSubmit}>
          <div className="composer">
            <div className="composer-controls">
              <label className="control">
                <span>Mode</span>
                <select
                  value={mode}
                  onChange={(e) => setMode(e.target.value)}
                  disabled={isLoading}
                >
                  {MODES.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="control">
                <span>Preset</span>
                <select
                  value={preset}
                  onChange={(e) => setPreset(e.target.value)}
                  disabled={isLoading}
                >
                  {PRESETS.map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <textarea
              className="message-input"
              placeholder={
                mode === 'extract'
                  ? 'Paste notes / chat log / discussion to extract a decision record...'
                  : mode === 'review'
                  ? 'Paste code / plan / draft to critique...'
                  : 'Ask your question... (Shift+Enter for new line, Enter to send)'
              }
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              rows={3}
            />
          </div>
          <button
            type="submit"
            className="send-button"
            disabled={!input.trim() || isLoading}
          >
            Send
          </button>
        </form>
      )}
    </div>
  );
}
