import { useState, useEffect, useCallback } from 'react';
import GraphPanel from './GraphPanel';
import ChatPanel from './ChatPanel';
import { fetchGraphData, sendChatMessage } from './api';
import './index.css';

export default function App() {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [highlightNodes, setHighlightNodes] = useState([]);

  /* Load graph on mount */
  useEffect(() => {
    fetchGraphData()
      .then(setGraphData)
      .catch((err) => console.error('Failed to load graph:', err));
  }, []);

  /* Chat handler */
  const handleSend = useCallback(async (query) => {
    /* Add user message */
    setMessages((prev) => [...prev, { role: 'user', text: query }]);
    setIsLoading(true);
    setHighlightNodes([]);

    try {
      const data = await sendChatMessage(query);

      /* Highlight nodes for trace intents */
      if (data.intent === 'trace' && data.result?.length > 0) {
        const nodeIds = new Set();
        data.result.forEach(({ from, to }) => {
          nodeIds.add(from);
          nodeIds.add(to);
        });
        setHighlightNodes([...nodeIds]);
      }

      setMessages((prev) => [...prev, { role: 'bot', data }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'bot', data: { error: err.message, answer: err.message } },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <div className="app">
      <GraphPanel graphData={graphData} highlightNodes={highlightNodes} />
      <ChatPanel onSend={handleSend} messages={messages} isLoading={isLoading} />
    </div>
  );
}
