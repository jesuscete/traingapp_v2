"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import type { User } from "@/lib/types";
import { logout as endSession } from "@/lib/session";

const TOKEN_KEY = "traingapp_token";
const USER_KEY = "traingapp_user";

export function AvatarMenu({ variant = "top" }: { variant?: "top" | "side" }) {
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
    void endSession().finally(() => router.replace("/"));
  }

  const initial = user?.name?.trim().charAt(0).toUpperCase() ?? "";

  return (
    <div className={`avatar-menu${variant === "side" ? " side" : ""}`}>
      <button
        type="button"
        className={`avatar-circle${variant === "side" ? " side" : ""}`}
        aria-label="Menú de usuario"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
      >
        {initial}
        {variant === "side" && <span className="avatar-menu-label">{user?.name ?? "Cuenta"}</span>}
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
            <Link className="avatar-menu-link" href="/cuenta">
              Cuenta
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
