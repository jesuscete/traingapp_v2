"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { AvatarMenu } from "@/components/AvatarMenu";
import { ChatWidget } from "@/components/ChatWidget";

type Tab = {
  href: string;
  label: string;
  match: string[];
};

const TABS: Tab[] = [
  { href: "/dashboard", label: "Inicio", match: ["/dashboard"] },
  { href: "/entrenar", label: "Entrenar", match: ["/entrenar", "/registro"] },
  { href: "/entrenos", label: "Historial", match: ["/entrenos"] },
  { href: "/rutinas", label: "Rutinas", match: ["/rutinas"] },
  { href: "/analisis", label: "Progreso", match: ["/analisis", "/fatiga"] },
];

function isMatch(pathname: string, match: string[]): boolean {
  return match.some((prefix) => pathname.startsWith(prefix));
}

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="tabbar" aria-label="Navegación principal">
      {TABS.map((tab) => {
        const active = isMatch(pathname, tab.match);
        return (
          <Link
            key={tab.href}
            className={`tabbar-link${active ? " active" : ""}`}
            href={tab.href}
          >
            {tab.label}
          </Link>
        );
      })}
      <AvatarMenu />
      <ChatWidget />
    </nav>
  );
}
