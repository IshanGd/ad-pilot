import type { Metadata } from "next";
import { Geist } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AdPilot — see where your Google Ads money goes",
  description:
    "Upload your Google Ads report and see exactly where your money is going. Free, no signup.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <header className="border-b border-border bg-surface">
          <div className="mx-auto flex max-w-3xl items-center justify-between px-5 py-4">
            <Link href="/" className="text-lg font-semibold tracking-tight">
              AdPilot
            </Link>
            <span className="text-sm text-muted">Free instant audit</span>
          </div>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="border-t border-border bg-surface">
          <div className="mx-auto max-w-3xl px-5 py-6 text-sm text-muted">
            AdPilot doesn&apos;t need your Google login or your password. Just the
            report you can export yourself.
          </div>
        </footer>
      </body>
    </html>
  );
}
