import { useMsal } from "@azure/msal-react";
import { useState } from "react";

import { api, type Citation } from "../services/api";

type Mode = "rag" | "agent";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  retrievalScore?: number;
}

export function ChatWindow() {
  const { instance } = useMsal();
  const [mode, setMode] = useState<Mode>("rag");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = async () => {
    const question = input.trim();
    if (!question || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      if (mode === "rag") {
        const result = await api.chatCompletion(instance, question);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: result.answer, citations: result.citations, retrievalScore: result.retrieval_score },
        ]);
      } else {
        const result = await api.agentChat(instance, question);
        setMessages((prev) => [...prev, { role: "assistant", content: result.answer }]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-window">
      <div className="mode-toggle">
        <button className={mode === "rag" ? "active" : ""} onClick={() => setMode("rag")}>
          RAG (always retrieves)
        </button>
        <button className={mode === "agent" ? "active" : ""} onClick={() => setMode("agent")}>
          Agent (chooses tools)
        </button>
      </div>

      <div className="messages">
        {messages.length === 0 && (
          <p className="empty-hint">
            Try: "What is the company's remote work policy?" or "What's our current AI spend this month?"
          </p>
        )}
        {messages.map((message, i) => (
          <div key={i} className={`message message--${message.role}`}>
            <div className="message__content">{message.content}</div>
            {message.citations && message.citations.length > 0 && (
              <div className="citations">
                {message.citations.map((c, j) => (
                  <span key={j} className="citation-chip">
                    {c.source ?? c.document_id} ({c.score.toFixed(2)})
                  </span>
                ))}
                {message.retrievalScore !== undefined && (
                  <span className="citation-chip citation-chip--muted">retrieval score {message.retrievalScore}</span>
                )}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="message message--assistant message--pending">Thinking…</div>}
        {error && <div className="message message--error">{error}</div>}
      </div>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
