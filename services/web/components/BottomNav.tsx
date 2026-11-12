"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Dumbbell, House, MessageCircle, TrendingUp, Utensils, type LucideIcon } from "lucide-react";

import { AvatarMenu } from "@/components/AvatarMenu";

type Tab = {
  href: string;
  label: string;
  Icon: LucideIcon;
  match: string[];
};

const TABS: Tab[] = [
  { href: "/dashboard", label: "Inicio", Icon: House, match: ["/dashboard"] },
  {
    href: "/entrenar",
    label: "Entrenar", Icon: Dumbbell,
    match: ["/entrenar", "/registrar", "/importar", "/rutinas", "/ejercicios"],
  },
  { href: "/comidas", label: "Comidas", Icon: Utensils, match: ["/comidas"] },
  {
    href: "/progreso",
    label: "Progreso", Icon: TrendingUp,
    match: ["/progreso", "/entrenos", "/analisis", "/fatiga", "/preparacion"],
  },
  { href: "/chat", label: "Coach", Icon: MessageCircle, match: ["/chat"] },
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
            <tab.Icon size={20} strokeWidth={1.75} aria-hidden="true" />
            <span>{tab.label}</span>
          </Link>
        );
      })}
      <AvatarMenu />
    </nav>
  );
}
