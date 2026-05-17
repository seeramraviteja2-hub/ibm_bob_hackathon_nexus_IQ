import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NexusIQ — AI Corporate Training",
  description: "AI-powered personalized learning platform for corporate teams",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
