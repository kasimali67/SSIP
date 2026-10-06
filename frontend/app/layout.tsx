import type { Metadata } from "next";

import "./globals.css";
import "./civic-theme.css";
import { muktaDevanagari, muktaGujarati } from "./fonts";

import { RagAssistant } from "@/components/chat/RagAssistant";
import { DemoModeBanner } from "@/components/civic/DemoModeBanner";
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
    <html
      lang="en"
      className={`${muktaDevanagari.variable} ${muktaGujarati.variable}`}
    >
      <body className="min-h-screen bg-background text-foreground antialiased">
        <LanguageProvider>
          <DemoModeBanner />
          <TopNav />
          <main className="container py-8">{children}</main>
          <RagAssistant />
        </LanguageProvider>
      </body>
    </html>
  );
}
