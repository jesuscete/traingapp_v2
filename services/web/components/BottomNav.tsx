"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

type Tab = {
  href?: string;
  label: string;
  match: string[];
  submenu?: { href: string; label: string }[];
};

const TABS: Tab[] = [
  { href: "/dashboard", label: "Inicio", match: ["/dashboard"] },
  {
    label: "Registrar",
    match: ["/chat", "/registro"],
    submenu: [
      { href: "/chat", label: "Chat o texto" },
      { href: "/registro/manual", label: "Manual" },
    ],
  },
  { href: "/entrenos", label: "Historial", match: ["/entrenos"] },
  { href: "/rutinas", label: "Rutinas", match: ["/rutinas"] },
  { href: "/analisis", label: "Progreso", match: ["/analisis", "/fatiga"] },
  { href: "/perfil", label: "Perfil", match: ["/perfil"] },
];

function isMatch(pathname: string, match: string[]): boolean {
  return match.some((prefix) => pathname.startsWith(prefix));
}

export function BottomNav() {
  const pathname = usePathname();
  const [openSubmenu, setOpenSubmenu] = useState(false);

  const activeRegistrar = isMatch(pathname, ["/chat", "/registro"]);

  useEffect(() => {
    if (activeRegistrar) setOpenSubmenu(true);
  }, [activeRegistrar]);

  return (
    <nav className="tabbar" aria-label="Navegación principal">
      {openSubmenu && (
        <div
          className="tabbar-backdrop"
          aria-hidden="true"
          onClick={() => setOpenSubmenu(false)}
        />
      )}
      {TABS.map((tab) => {
        const active = isMatch(pathname, tab.match);
        if (tab.submenu) {
          return (
            <div key={tab.label} className="tabbar-item">
              <button
                type="button"
                className={`tabbar-link${active ? " active" : ""}`}
                aria-expanded={openSubmenu}
                onClick={() => setOpenSubmenu((prev) => !prev)}
              >
                {tab.label}
                <span className="tabbar-caret">▾</span>
              </button>
              {openSubmenu && (
                <div className="tabbar-submenu">
                  {tab.submenu.map((item) => (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`tabbar-submenu-link${isMatch(pathname, [item.href]) ? " active" : ""}`}
                      onClick={() => setOpenSubmenu(false)}
                    >
                      {item.label}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          );
        }
        return (
          <Link
            key={tab.href}
            className={`tabbar-link${active ? " active" : ""}`}
            href={tab.href!}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
