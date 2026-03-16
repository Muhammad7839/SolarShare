// Floating SolarShare assistant that provides navigation and comparison guidance on every page.
"use client";

import { MessageCircle, Send, Sparkles, X } from "lucide-react";
import { usePathname } from "next/navigation";
import { useMemo, useState } from "react";
import { sendAssistantChat } from "@/lib/api";

type ChatMessage = {
  id: string;
  role: "assistant" | "user";
  content: string;
};

const quickPrompts = [
  "How do I run live comparison?",
  "Help me with ZIP code accuracy",
  "Where can I contact your team?"
];

function localFallbackReply(message: string): { reply: string; suggested_actions: string[] } {
  const normalized = message.toLowerCase();
  if (normalized.includes("zip") || normalized.includes("location")) {
    return {
      reply: "Enter either city/state or ZIP. For best accuracy, use ZIP and click Preview Location before running comparison.",
      suggested_actions: ["Preview location", "Run live comparison", "See confidence score"]
    };
  }
  if (normalized.includes("contact") || normalized.includes("support")) {
    return {
      reply: "Use the Contact page to submit inquiries for support, partnerships, or investor relations.",
      suggested_actions: ["Open contact page", "Submit inquiry"]
    };
  }
  return {
    reply: "I can help you run a comparison, verify location accuracy, and find the right page quickly.",
    suggested_actions: ["Run live comparison", "Location help", "Contact team"]
  };
}

function getSessionId(): string {
  if (typeof window === "undefined") {
    return "ss-server";
  }
  try {
    const key = "solarshare_session_id_v2";
    const existing = window.localStorage.getItem(key);
    if (existing) {
      return existing;
    }
    const created = `ss-${Math.random().toString(36).slice(2, 10)}`;
    window.localStorage.setItem(key, created);
    return created;
  } catch {
    return "ss-browser";
  }
}

export function AssistantWidget() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Hi, I am SolarShare Assistant. Ask me anything about comparison, ZIP resolution, or navigation."
    }
  ]);

  const canSend = input.trim().length >= 2 && !loading;

  const lastAssistantActions = useMemo(() => {
    const lastAssistant = [...messages].reverse().find((item) => item.role === "assistant");
    if (!lastAssistant) {
      return [];
    }
    if (lastAssistant.content.includes("Preview location")) {
      return ["Preview location", "Run live comparison"];
    }
    return [];
  }, [messages]);

  async function sendMessage(raw: string) {
    const message = raw.trim();
    if (message.length < 2 || loading) {
      return;
    }

    const userMessage: ChatMessage = {
      id: `${Date.now()}-user`,
      role: "user",
      content: message
    };
    setMessages((previous) => [...previous, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const payload = await sendAssistantChat({
        message,
        page: pathname,
        context: { session_id: getSessionId() }
      });

      setMessages((previous) => [
        ...previous,
        {
          id: `${Date.now()}-assistant`,
          role: "assistant",
          content: payload.reply
        }
      ]);
    } catch {
      const fallback = localFallbackReply(message);
      setMessages((previous) => [
        ...previous,
        {
          id: `${Date.now()}-assistant-fallback`,
          role: "assistant",
          content: fallback.reply
        }
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <button
        type="button"
        aria-label={open ? "Close assistant" : "Open assistant"}
        onClick={() => setOpen((previous) => !previous)}
        className="assistant-fab"
      >
        {open ? <X className="size-5" /> : <MessageCircle className="size-5" />}
      </button>

      {open ? (
        <aside className="assistant-panel" aria-label="SolarShare assistant">
          <div className="assistant-panel-header">
            <div className="assistant-title-wrap">
              <Sparkles className="size-4" />
              <p>SolarShare Assistant</p>
            </div>
            <button type="button" className="assistant-close" onClick={() => setOpen(false)} aria-label="Close assistant panel">
              <X className="size-4" />
            </button>
          </div>

          <div className="assistant-quick-prompts">
            {quickPrompts.map((prompt) => (
              <button key={prompt} type="button" onClick={() => sendMessage(prompt)}>
                {prompt}
              </button>
            ))}
          </div>

          <div className="assistant-messages" role="log" aria-live="polite">
            {messages.map((message) => (
              <article key={message.id} className={`assistant-bubble ${message.role === "user" ? "user" : "assistant"}`}>
                {message.content}
              </article>
            ))}
            {loading ? <article className="assistant-bubble assistant">Thinking...</article> : null}
          </div>

          {lastAssistantActions.length ? (
            <div className="assistant-actions">
              {lastAssistantActions.map((action) => (
                <span key={action}>{action}</span>
              ))}
            </div>
          ) : null}

          <form
            className="assistant-input"
            onSubmit={(event) => {
              event.preventDefault();
              void sendMessage(input);
            }}
          >
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask for help..."
              minLength={2}
              maxLength={320}
            />
            <button type="submit" disabled={!canSend} aria-label="Send message">
              <Send className="size-4" />
            </button>
          </form>
        </aside>
      ) : null}
    </>
  );
}
