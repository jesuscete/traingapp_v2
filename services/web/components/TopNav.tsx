"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function TopNav({ onLogout }: { onLogout: () => void }) {
  const pathname = usePathname();

  const linkClass = (path: string) =>
    `nav-link${pathname === path ? " active" : ""}`;

  return (
    <header className="topbar">
      <h1>TraingApp</h1>
      <nav className="nav">
        <Link className={linkClass("/dashboard")} href="/dashboard">
          Inicio
        </Link>
        <Link className={linkClass("/chat")} href="/chat">
          Registrar
        </Link>
        <Link className={linkClass("/entrenos")} href="/entrenos">
          Entrenos
        </Link>
        <Link className={linkClass("/fatiga")} href="/fatiga">
          Fatiga
        </Link>
        <Link className={linkClass("/perfil")} href="/perfil">
          Perfil
        </Link>
        <button type="button" className="link" onClick={onLogout}>
          Salir
        </button>
      </nav>
    </header>
  );
}
