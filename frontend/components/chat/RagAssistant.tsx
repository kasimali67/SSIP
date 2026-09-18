"use client";

import { useState, type FormEvent } from "react";
import { FileText, MessageCircle, Send, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { queryRag } from "@/lib/api";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: string[];
}

export function RagAssistant() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading) {
      return;
    }

    setQuestion("");
    setError(null);
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", content: trimmed },
    ]);
    setLoading(true);

    try {
      const response = await queryRag(trimmed);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer,
          sources: response.sources,
        },
      ]);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "The assistant is unavailable.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Button
        type="button"
        size="icon"
        className="fixed bottom-6 right-6 z-50 h-12 w-12 rounded-full shadow-lg"
        onClick={() => setOpen((current) => !current)}
        aria-label={open ? "Close assistant" : "Open assistant"}
      >
        {open ? (
          <X className="h-5 w-5" />
        ) : (
          <MessageCircle className="h-5 w-5" />
        )}
      </Button>

      {open ? (
        <aside className="fixed bottom-24 right-6 z-50 flex h-[28rem] w-[22rem] max-w-[calc(100vw-3rem)] flex-col rounded-xl border bg-card shadow-xl">
          <header className="flex items-center gap-2 border-b p-3">
            <MessageCircle className="h-4 w-4" />
            <span className="text-sm font-semibold">Assistant</span>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto p-3">
            {messages.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Ask about government forms and procedures.
              </p>
            ) : null}

            {messages.map((message) => (
              <div
                key={message.id}
                className={
                  message.role === "user"
                    ? "ml-auto max-w-[85%] rounded-lg bg-primary p-2 text-sm text-primary-foreground"
                    : "mr-auto max-w-[85%] rounded-lg bg-muted p-2 text-sm"
                }
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
                {message.sources && message.sources.length > 0 ? (
                  <ul className="mt-2 space-y-1 border-t pt-2 text-xs text-muted-foreground">
                    {message.sources.map((source) => (
                      <li key={source} className="flex items-center gap-1">
                        <FileText className="h-3 w-3" />
                        {source}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ))}

            {loading ? (
              <div className="mr-auto max-w-[85%] space-y-2 rounded-lg bg-muted p-3">
                <Skeleton className="h-3 w-40" />
                <Skeleton className="h-3 w-28" />
              </div>
            ) : null}
          </div>

          {error ? (
            <p className="px-3 pb-2 text-xs text-destructive">{error}</p>
          ) : null}

          <form
            onSubmit={handleSubmit}
            className="flex items-center gap-2 border-t p-3"
          >
            <Input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask a question…"
              aria-label="Question"
            />
            <Button
              type="submit"
              size="icon"
              disabled={loading || question.trim().length === 0}
              aria-label="Send"
            >
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </aside>
      ) : null}
    </>
  );
}
