import type { Metadata } from "next";
import { SplashScreen } from "./components/splash-screen";
import "./globals.css";

export const metadata: Metadata = {
  title: "SandBench — RL benchmarking in an isolated sandbox",
  description:
    "Submit code, files, an API, or your own model. SandBench runs it in a hardened throwaway container, flags anything malicious, reviews what's messy, and scores it on a leaderboard.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className="h-full antialiased dark"
    >
      <body className="min-h-full flex flex-col">
        <SplashScreen />
        {children}
      </body>
    </html>
  );
}
