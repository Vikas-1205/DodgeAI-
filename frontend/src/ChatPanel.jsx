import { useState, useRef, useEffect } from 'react';

const EXAMPLES = [
    'Show all customers',
    'Top 3 products by price',
    'trace order 1',
    'show full flow of order 4',
    'Total revenue by customer',
];

export default function ChatPanel({ onSend, messages, isLoading }) {
    const [input, setInput] = useState('');
    const messagesEndRef = useRef(null);

    /* Auto-scroll to bottom */
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading]);

    const handleSubmit = (e) => {
        e.preventDefault();
        const q = input.trim();
        if (!q || isLoading) return;
        onSend(q);
        setInput('');
    };

    const handleExample = (q) => {
        if (isLoading) return;
        setInput(q);
        onSend(q);
    };

    return (
        <div className="chat-panel">
            <div className="chat-panel__header">
                <div className="chat-panel__title">Chat</div>
                <div className="chat-panel__subtitle">
                    Ask questions or trace entity flows
                </div>
            </div>

            <div className="chat-messages">
                {messages.length === 0 && !isLoading && (
                    <div className="welcome">
                        <div className="welcome__icon">💬</div>
                        <div className="welcome__title">Ask anything about your data</div>
                        <p style={{ fontSize: '12.5px', color: '#6b7089', marginTop: '4px' }}>
                            Try a question or trace a flow
                        </p>
                        <ul className="welcome__examples">
                            {EXAMPLES.map((ex) => (
                                <li
                                    key={ex}
                                    className="welcome__example"
                                    onClick={() => handleExample(ex)}
                                >
                                    {ex}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {messages.map((msg, i) => (
                    <MessageBubble key={i} msg={msg} />
                ))}

                {isLoading && (
                    <div className="message message--bot">
                        <div className="loading-dots">
                            <span /><span /><span />
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            <div className="chat-input-area">
                <form className="chat-input-form" onSubmit={handleSubmit}>
                    <input
                        id="chat-input"
                        className="chat-input"
                        type="text"
                        placeholder="Ask a question or trace an entity..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        disabled={isLoading}
                        autoComplete="off"
                    />
                    <button
                        id="chat-send"
                        className="chat-send-btn"
                        type="submit"
                        disabled={isLoading || !input.trim()}
                    >
                        Send
                    </button>
                </form>
            </div>
        </div>
    );
}


/* ─── Message Bubble ─────────────────────────────────────────────────── */

function MessageBubble({ msg }) {
    if (msg.role === 'user') {
        return <div className="message message--user">{msg.text}</div>;
    }

    const data = msg.data || {};
    const isError = !!data.error;
    const isTrace = data.intent === 'trace';

    return (
        <div className={`message message--bot ${isError ? 'message--error' : ''}`}>
            {/* Intent badge */}
            {data.intent && (
                <div className={`message__intent message__intent--${data.intent}`}>
                    {data.intent}
                </div>
            )}

            {/* Answer text */}
            <div className="message__answer">{data.answer || data.error || msg.text}</div>

            {/* SQL query (for query intents) */}
            {data.sql && (
                <>
                    <div className="message__sql-label">SQL Query</div>
                    <div className="message__sql">{data.sql}</div>
                </>
            )}

            {/* Trace chain (for trace intents) */}
            {isTrace && data.result && data.result.length > 0 && (
                <TraceChain steps={data.result} />
            )}
        </div>
    );
}


/* ─── Trace Chain Visualization ──────────────────────────────────────── */

const STEP_COLORS = {
    Order: '#e8a44c', Customer: '#6c7bea', Product: '#4cce8a',
    Delivery: '#5cc8e8', Invoice: '#e85ca4', Payment: '#c85ce8',
};

function TraceChain({ steps }) {
    /* Build an ordered list of unique nodes from the edge list */
    const seen = new Set();
    const orderedNodes = [];

    steps.forEach(({ from, to, relationship }) => {
        if (!seen.has(from)) { seen.add(from); orderedNodes.push(from); }
        if (!seen.has(to)) { seen.add(to); orderedNodes.push(to); }
    });

    return (
        <div className="trace-chain">
            {orderedNodes.map((nodeId, i) => {
                const [type] = nodeId.split(':');
                const color = STEP_COLORS[type] || '#888';
                const rel = i < steps.length ? steps[i]?.relationship : '';

                return (
                    <div key={nodeId}>
                        <div className="trace-step">
                            <span className="trace-step__dot" style={{ background: color }} />
                            <span>{nodeId}</span>
                        </div>
                        {i < orderedNodes.length - 1 && (
                            <div className="trace-step__arrow">
                                ↓ <span style={{ fontSize: '10px', color: '#6b7089' }}>{rel}</span>
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
