"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { ArrowLeft, Dumbbell, House, MessageCircle, TrendingUp, Utensils, type LucideIcon } from "lucide-react";

import { AvatarMenu } from "@/components/AvatarMenu";

type Tab = {
  href: string;
  label: string;
  Icon: LucideIcon;
  match: string[];
};

const TABS: Tab[] = [
  { href: "/dashboard", label: "Hoy", Icon: House, match: ["/dashboard"] },
  {
    href: "/entrenar",
    label: "Entrenar",
    Icon: Dumbbell,
    match: ["/entrenar", "/registrar", "/importar", "/rutinas", "/ejercicios", "/entrenos"],
  },
  { href: "/comidas", label: "Comidas", Icon: Utensils, match: ["/comidas"] },
  {
    href: "/progreso",
    label: "Progreso",
    Icon: TrendingUp,
    match: ["/progreso", "/analisis", "/fatiga", "/preparacion"],
  },
  { href: "/chat", label: "Coach", Icon: MessageCircle, match: ["/chat"] },
];

const ACCOUNT_MATCH = ["/cuenta", "/perfil", "/objetivos", "/configuracion"];

// Subpantallas con nombre propio en la barra superior.
const SUBPAGE_TITLES: Record<string, string> = { "/rutinas": "Rutina" };

function isMatch(pathname: string, match: string[]): boolean {
  return match.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

function currentTab(pathname: string): Tab | undefined {
  return TABS.find((tab) => isMatch(pathname, tab.match));
}

export function BottomNav({ hidden = false }: { hidden?: boolean }) {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!hidden) return;
    document.body.classList.add("nav-hidden");
    return () => document.body.classList.remove("nav-hidden");
  }, [hidden]);

  if (hidden) return null;

  const tab = currentTab(pathname);
  const isAccount = isMatch(pathname, ACCOUNT_MATCH);
  const title = isAccount ? "Cuenta" : (SUBPAGE_TITLES[pathname] ?? tab?.label ?? "");
  const rootHref = tab?.href ?? "/dashboard";
  const isAccountSub = isAccount && pathname.startsWith("/cuenta/");
  const isSubpage = isAccount ? isAccountSub : tab !== undefined && pathname !== tab.href;

  function goBack() {
    if (isAccountSub) router.push("/cuenta");
    else if (window.history.length > 1) router.back();
    else router.push(rootHref);
  }

  return (
    <>
      <header className="app-topbar">
        {isSubpage && (
          <button type="button" className="app-topbar-back" aria-label="Volver" onClick={goBack}>
            <ArrowLeft size={24} strokeWidth={1.75} aria-hidden="true" />
          </button>
        )}
        <h1 className="app-topbar-title">{title}</h1>
        <AvatarMenu />
      </header>

      <nav className="app-nav" aria-label="Navegación principal">
        <Link className="app-nav-brand" href="/dashboard">
          <img className="app-nav-logo" src="/logo-mark.png" alt="" width={28} height={28} />
          <span>Athlys</span>
        </Link>
        <ul className="app-nav-list">
          {TABS.map((t) => {
            const active = isMatch(pathname, t.match);
            return (
              <li key={t.href} className="app-nav-item">
                <Link
                  className={`app-nav-link${active ? " active" : ""}`}
                  href={t.href}
                  aria-current={active ? "page" : undefined}
                >
                  <span className="app-nav-icon">
                    <t.Icon size={22} strokeWidth={1.75} aria-hidden="true" />
                  </span>
                  <span>{t.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
        <div className="app-nav-account">
          <AvatarMenu variant="side" />
        </div>
      </nav>
    </>
  );
}
