"use client";

import { useRef, useState } from "react";
import { MessageSquare, PanelLeftClose, PanelLeftOpen, Plus } from "lucide-react";

import { ChatInterface, type ChatHandle } from "@/components/chat/ChatInterface";
import { LanguageSwitcher } from "@/components/civic/LanguageSwitcher";
import { Button } from "@/components/ui/button";

const QUICK_PROMPTS = [
  "Update Aadhaar Address",
  "Check Ration Card Eligibility",
  "Track my application status",
  "PAN card correction",
];

export default function Home() {
  const chatRef = useRef<ChatHandle>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [history, setHistory] = useState<string[]>(["Aadhaar address update"]);

  function newChat() {
    chatRef.current?.reset();
    setHistory((items) => ["New chat", ...items]);
  }

  return (
    <div className="flex h-[calc(100dvh-3.5rem)] -mx-8 -my-8 overflow-hidden">
      {sidebarOpen ? (
        <aside className="flex w-72 shrink-0 flex-col border-r bg-[var(--civic-paper)]">
          <div className="flex items-center justify-between border-b p-3">
            <span className="font-semibold">History</span>
            <button
              type="button"
              onClick={() => setSidebarOpen(false)}
              aria-label="Collapse sidebar"
              className="rounded-md p-1 hover:bg-accent"
            >
              <PanelLeftClose className="h-5 w-5" />
            </button>
          </div>

          <div className="p-3">
            <Button
              variant="outline"
              className="w-full justify-start gap-2"
              onClick={newChat}
            >
              <Plus className="h-4 w-4" />
              New Chat
            </Button>
          </div>

          <nav className="flex-1 overflow-y-auto px-3">
            <p className="px-1 text-xs uppercase text-muted-foreground">Recent</p>
            <ul className="mt-1 space-y-1">
              {history.map((item) => (
                <li key={item}>
                  <button
                    type="button"
                    className="flex w-full items-center gap-1 truncate rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent"
                  >
                    <MessageSquare className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">{item}</span>
                  </button>
                </li>
              ))}
            </ul>

            <p className="mt-4 px-1 text-xs uppercase text-muted-foreground">
              Quick prompts
            </p>
            <ul className="mt-1 space-y-1">
              {QUICK_PROMPTS.map((prompt) => (
                <li key={prompt}>
                  <button
                    type="button"
                    onClick={() => chatRef.current?.quickPrompt(prompt)}
                    className="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent"
                  >
                    {prompt}
                  </button>
                </li>
              ))}
            </ul>
          </nav>

          <div className="border-t p-3">
            <LanguageSwitcher />
          </div>
        </aside>
      ) : (
        <button
          type="button"
          onClick={() => setSidebarOpen(true)}
          aria-label="Open sidebar"
          className="m-2 shrink-0 rounded-md border p-2 hover:bg-accent"
        >
          <PanelLeftOpen className="h-5 w-5" />
        </button>
      )}

      <ChatInterface ref={chatRef} />
    </div>
  );
}
