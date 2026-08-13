"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import type { User } from "@/lib/types";

const TOKEN_KEY = "traingapp_token";
const USER_KEY = "traingapp_user";

export function AvatarMenu() {
  const router = useRouter();
  const pathname = usePathname();
  const [visible, setVisible] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) return;
    const storedUser = localStorage.getItem(USER_KEY);
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        setUser(null);
      }
    }
    setVisible(true);
  }, []);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  if (!visible) return null;

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    router.replace("/");
  }

  const initial = user?.name?.trim().charAt(0).toUpperCase() ?? "";

  return (
    <div className="avatar-menu">
      <button
        type="button"
        className="avatar-circle"
        aria-label="Menú de usuario"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
      >
        {initial}
      </button>
      {open && (
        <>
          <div
            className="avatar-menu-backdrop"
            aria-hidden="true"
            onClick={() => setOpen(false)}
          />
          <div className="avatar-menu-dropdown">
            <div className="avatar-menu-user">
              <span className="avatar-menu-name">{user?.name ?? "Usuario"}</span>
              {user?.email && (
                <span className="avatar-menu-email">{user.email}</span>
              )}
            </div>
            <Link className="avatar-menu-link" href="/perfil">
              Perfil
            </Link>
            <Link className="avatar-menu-link" href="/configuracion">
              Configuración
            </Link>
            <button
              type="button"
              className="avatar-menu-link danger"
              onClick={logout}
            >
              Cerrar sesión
            </button>
          </div>
        </>
      )}
    </div>
  );
}
