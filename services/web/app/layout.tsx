import type { Metadata, Viewport } from "next";
import { Barlow_Condensed, Geist, Geist_Mono, Inter } from "next/font/google";
import { PendingSync } from "@/components/PendingSync";
import { ThemeProvider } from "@/components/ThemeProvider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const inter = Inter({
  variable: "--font-body",
  subsets: ["latin"],
  display: "swap",
});

const barlowCondensed = Barlow_Condensed({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "TraingApp",
  description: "Registra y analiza tus entrenamientos con IA",
  appleWebApp: { capable: true, title: "TrainingApp", statusBarStyle: "black-translucent" },
  icons: { icon: "/icon.svg", apple: "/icon.svg" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#15161a",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="es"
      className={`${geistSans.variable} ${geistMono.variable} ${inter.variable} ${barlowCondensed.variable}`}
    >
      <body>
        <ThemeProvider />
        <PendingSync />
        {children}
      </body>
    </html>
  );
}
