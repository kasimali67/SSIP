"use client";

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
} from "react";
import {
  CircleCheck,
  Mic,
  Paperclip,
  Send,
  ShieldCheck,
  TriangleAlert,
  UploadCloud,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export type OcrFields = {
  name: string;
  dob: string;
  idNumber: string;
};

export type BotContent =
  | { type: "text"; text: string }
  | { type: "uploadPrompt" }
  | { type: "ocrResult" }
  | { type: "digilocker" }
  | { type: "receipt"; urn: string };

export type ChatMessage =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "bot"; content: BotContent };

export type ChatHandle = {
  reset: () => void;
  quickPrompt: (text: string) => void;
};

const MOCK_OCR: OcrFields = {
  name: "Ramesh Kumar Patel",
  dob: "15/08/1985",
  idNumber: "XXXX-XXXX-4821",
};

const MOCK_CONFIDENCES: Record<keyof OcrFields, number> = {
  name: 0.93,
  dob: 0.71,
  idNumber: 0.96,
};

const LOW_CONFIDENCE = 0.75;

function id(): string {
  return crypto.randomUUID();
}

function initialMessages(): ChatMessage[] {
  return [
    {
      id: id(),
      role: "bot",
      content: {
        type: "text",
        text: "Hi! I can help you update your Aadhaar address or check your ration card eligibility. Upload a document to get started.",
      },
    },
    { id: id(), role: "bot", content: { type: "uploadPrompt" } },
  ];
}

function mockReply(text: string): string {
  return `I can help with "${text}". Upload a document and I will walk you through verification step by step.`;
}

function genUrn(): string {
  const slug = crypto.randomUUID().replace(/-/g, "").slice(0, 12).toUpperCase();
  return `URN-${slug}`;
}

interface SpeechRecognitionEventLike {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
}

interface SpeechRecognitionInstance {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance;

function createSpeechRecognition(): SpeechRecognitionInstance | null {
  if (typeof window === "undefined") {
    return null;
  }
  const scope = window as unknown as {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  };
  const Constructor = scope.SpeechRecognition ?? scope.webkitSpeechRecognition;
  return Constructor ? new Constructor() : null;
}

function UploadPrompt({ onFile }: { onFile: (file: File) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const dropped = event.dataTransfer.files.item(0);
    if (dropped) {
      onFile(dropped);
    }
  }

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.item(0);
    if (chosen) {
      onFile(chosen);
    }
    event.target.value = "";
  }

  return (
    <div className="space-y-2">
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            inputRef.current?.click();
          }
        }}
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
        className="flex cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border-2 border-dashed border-slate-400 bg-white p-6 text-center hover:border-[var(--civic-ink)]"
      >
        <UploadCloud className="h-7 w-7 text-muted-foreground" />
        <p className="text-sm font-medium">Drop a document here or click to upload</p>
        <p className="text-xs text-muted-foreground">PNG, JPG or PDF</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/*,.pdf"
        className="hidden"
        onChange={handleChange}
      />
    </div>
  );
}

function OcrResultCard({ onConfirm }: { onConfirm: () => void }) {
  const [fields, setFields] = useState<OcrFields>(MOCK_OCR);

  function updateField(key: keyof OcrFields, value: string) {
    setFields((current) => ({ ...current, [key]: value }));
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium">I read these details from your document. Check and correct them.</p>
      {(Object.keys(fields) as Array<keyof OcrFields>).map((key) => {
        const confidence = MOCK_CONFIDENCES[key];
        const low = confidence < LOW_CONFIDENCE;
        return (
          <div key={key} className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase text-muted-foreground">
                {key === "name" ? "Full name" : key === "dob" ? "Date of birth" : "ID number"}
              </span>
              <Badge variant={low ? "warning" : "secondary"}>
                {low ? <TriangleAlert className="h-3 w-3" /> : null}
                {Math.round(confidence * 100)}%
              </Badge>
            </div>
            <Input
              value={fields[key]}
              inputMode={key === "idNumber" ? "numeric" : "text"}
              onChange={(event) => updateField(key, event.target.value)}
              className={low ? "border-orange-400" : undefined}
            />
          </div>
        );
      })}
      <Button type="button" className="w-full" onClick={onConfirm}>
        Confirm
      </Button>
    </div>
  );
}

function DigiLockerCard({
  onMatch,
  onMismatch,
}: {
  onMatch: () => void;
  onMismatch: () => void;
}) {
  const [otp, setOtp] = useState("");
  const ready = /^\d{6}$/.test(otp);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <ShieldCheck className="h-5 w-5 text-[var(--civic-ink)]" />
        <p className="text-sm font-medium">DigiLocker verification</p>
      </div>
      <p className="text-sm text-muted-foreground">
        Enter the 6-digit OTP shown in your DigiLocker app.
      </p>
      <Input
        value={otp}
        inputMode="numeric"
        maxLength={6}
        placeholder="••••••"
        className="text-center text-lg tracking-[0.5em]"
        onChange={(event) => setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))}
      />
      <div className="flex gap-2">
        <Button
          type="button"
          className="flex-1"
          disabled={!ready}
          onClick={onMatch}
        >
          Simulate Match
        </Button>
        <Button
          type="button"
          variant="outline"
          className="flex-1"
          disabled={!ready}
          onClick={onMismatch}
        >
          Simulate Mismatch
        </Button>
      </div>
    </div>
  );
}

function ReceiptCard({ urn }: { urn: string }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border-2 border-green-600 bg-green-50 p-4">
      <CircleCheck className="mt-0.5 h-6 w-6 shrink-0 text-green-700" />
      <div>
        <p className="font-semibold text-green-900">Request submitted</p>
        <p className="mt-1 text-sm text-green-900/80">
          Your update request number is:
        </p>
        <p className="mt-1 rounded-md bg-white px-2 py-1 font-mono text-sm">{urn}</p>
      </div>
    </div>
  );
}

export const ChatInterface = forwardRef<ChatHandle>(function ChatInterface(
  _props,
  ref,
) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [input, setInput] = useState("");
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const appendUser = useCallback((text: string) => {
    setMessages((current) => [...current, { id: id(), role: "user", text }]);
  }, []);

  const appendBot = useCallback((content: BotContent) => {
    setMessages((current) => [
      ...current,
      { id: id(), role: "bot", content },
    ]);
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      reset: () => {
        setMessages(initialMessages());
        setError(null);
      },
      quickPrompt: (text: string) => {
        appendUser(text);
        appendBot({ type: "text", text: mockReply(text) });
      },
    }),
    [appendUser, appendBot],
  );

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleFile(file: File) {
    appendUser(`Attached: ${file.name}`);
    appendBot({ type: "ocrResult" });
  }

  function handleSend() {
    const trimmed = input.trim();
    if (!trimmed) {
      return;
    }
    appendUser(trimmed);
    appendBot({ type: "text", text: mockReply(trimmed) });
    setInput("");
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.item(0);
    if (chosen) {
      handleFile(chosen);
    }
    event.target.value = "";
  }

  function toggleMic() {
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }
    const recognition = createSpeechRecognition();
    if (!recognition) {
      setError("Speech recognition is not supported in this browser.");
      return;
    }
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript ?? "";
      if (transcript) {
        setInput((current) => (current ? `${current} ${transcript}` : transcript));
      }
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }

  return (
    <div className="flex min-w-0 flex-1 flex-col bg-[var(--civic-field)]">
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.map((message) => {
          if (message.role === "user") {
            return (
              <div key={message.id} className="flex justify-end">
                <div className="max-w-[75%] rounded-2xl bg-[var(--civic-ink)] px-4 py-2 text-sm text-white">
                  {message.text}
                </div>
              </div>
            );
          }

          return (
            <div key={message.id} className="flex justify-start">
              <div className="max-w-[85%] rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm">
                {message.content.type === "text" ? <p>{message.content.text}</p> : null}
                {message.content.type === "uploadPrompt" ? (
                  <UploadPrompt onFile={handleFile} />
                ) : null}
                {message.content.type === "ocrResult" ? (
                  <OcrResultCard onConfirm={() => appendBot({ type: "digilocker" })} />
                ) : null}
                {message.content.type === "digilocker" ? (
                  <DigiLockerCard
                    onMatch={() => appendBot({ type: "receipt", urn: genUrn() })}
                    onMismatch={() =>
                      appendBot({
                        type: "text",
                        text: "Some details do not match the official record. Please correct them and try again.",
                      })
                    }
                  />
                ) : null}
                {message.content.type === "receipt" ? (
                  <ReceiptCard urn={message.content.urn} />
                ) : null}
              </div>
            </div>
          );
        })}
        <div ref={endRef} />
      </div>

      {error ? (
        <p className="px-4 pb-1 text-xs text-destructive">{error}</p>
      ) : null}

      <div className="sticky bottom-0 border-t bg-[var(--civic-paper)] p-3">
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label="Attach a document"
            onClick={() => fileInputRef.current?.click()}
          >
            <Paperclip className="h-5 w-5" />
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,.pdf"
            className="hidden"
            onChange={handleFileChange}
          />
          <Input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                handleSend();
              }
            }}
            placeholder="Ask about a government service…"
            className="flex-1"
          />
          <Button
            type="button"
            variant={listening ? "default" : "ghost"}
            size="icon"
            aria-label="Voice input"
            onClick={toggleMic}
          >
            <Mic className="h-5 w-5" />
          </Button>
          <Button
            type="button"
            size="icon"
            aria-label="Send"
            disabled={input.trim().length === 0}
            onClick={handleSend}
          >
            <Send className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </div>
  );
});
