import type { Metadata } from "next";

import "./globals.css";

import { RagAssistant } from "@/components/chat/RagAssistant";
import { TopNav } from "@/components/layout/TopNav";
import { LanguageProvider } from "@/lib/LanguageContext";

export const metadata: Metadata = {
  title: "SSIP GovTech Platform",
  description:
    "Multilingual OCR and RAG assistant for Indian government form applications.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background text-foreground antialiased">
        <LanguageProvider>
          <TopNav />
          <main className="container py-8">{children}</main>
          <RagAssistant />
        </LanguageProvider>
      </body>
    </html>
  );
}
