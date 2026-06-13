import type { Metadata } from "next";
import { Poppins, Geist_Mono } from "next/font/google";
import { SplashScreen } from "./components/splash-screen";
import "./globals.css";

const poppins = Poppins({
  weight: ["300", "400", "500", "600", "700", "800"],
  variable: "--font-poppins",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

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
      className={`${poppins.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full flex flex-col">
        <SplashScreen />
        {children}
      </body>
    </html>
  );
}
