import type { Metadata } from "next";

import "./globals.css";

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
      <body>{children}</body>
    </html>
  );
}
