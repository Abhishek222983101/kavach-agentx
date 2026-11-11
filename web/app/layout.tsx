import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Instrument_Serif } from "next/font/google";
import { ThemeProvider } from "next-themes";
import { Suspense } from "react";
import "./globals.css";
import Shell from "@/components/Shell";
import ThemedToaster from "@/components/ThemedToaster";

const serif = Instrument_Serif({ variable: "--font-instrument", subsets: ["latin"], weight: "400", style: ["italic"] });

export const metadata: Metadata = {
  title: "Kavach: the support agent that can't be fooled",
  description: "A WhatsApp support agent for small sellers that checks every refund, return and address change against the records before it acts. Team Paradigm, AgentX 2026.",
  authors: [{ name: "Team Paradigm" }],
};
export const viewport: Viewport = {
  themeColor: [{ media: "(prefers-color-scheme: dark)", color: "#0a0a0b" }, { media: "(prefers-color-scheme: light)", color: "#f7f6f3" }],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${GeistSans.variable} ${GeistMono.variable} ${serif.variable} h-full`}>
      <body className="min-h-full">
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false} disableTransitionOnChange>
          <Suspense><Shell>{children}</Shell></Suspense>
          <ThemedToaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
