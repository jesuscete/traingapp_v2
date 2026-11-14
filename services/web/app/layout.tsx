import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Manrope, Sora } from "next/font/google";
import { PendingSync } from "@/components/PendingSync";
import { ServiceWorker } from "@/components/ServiceWorker";
import { ThemeProvider } from "@/components/ThemeProvider";
import { THEME_BOOT_SCRIPT } from "@/lib/theme";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const manrope = Manrope({
  variable: "--font-body",
  subsets: ["latin"],
  display: "swap",
});

const sora = Sora({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Athlys",
  description: "Registra y analiza tus entrenamientos con IA",
  appleWebApp: { capable: true, title: "Athlys", statusBarStyle: "black-translucent" },
  icons: { icon: "/favicon-64.png", apple: "/apple-touch-icon.png" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#121317",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="es"
      className={`${geistSans.variable} ${geistMono.variable} ${manrope.variable} ${sora.variable}`}
      suppressHydrationWarning
    >
      <head>
        {/* Aplica el tema guardado antes de pintar (sin parpadeo). */}
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT_SCRIPT }} />
      </head>
      <body>
        <ThemeProvider />
        <PendingSync />
        <ServiceWorker />
        {children}
      </body>
    </html>
  );
}
