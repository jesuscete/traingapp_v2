"use client";

import Link from "next/link";
import { ChevronRight, Palette, ShieldCheck, Target, User, Watch, type LucideIcon } from "lucide-react";

import { BottomNav } from "@/components/BottomNav";

type Item = { href: string; Icon: LucideIcon; title: string; desc: string };

const GROUPS: { label: string; items: Item[] }[] = [
  {
    label: "Tú",
    items: [
      { href: "/cuenta/perfil", Icon: User, title: "Perfil", desc: "Datos físicos y frecuencia cardiaca" },
      { href: "/cuenta/objetivos", Icon: Target, title: "Objetivos y deporte", desc: "Deporte principal y metas" },
    ],
  },
  {
    label: "Aplicación",
    items: [
      { href: "/cuenta/conexiones", Icon: Watch, title: "Conexiones", desc: "Garmin y otros servicios" },
      { href: "/cuenta/apariencia", Icon: Palette, title: "Apariencia y app", desc: "Tema, color e instalar la app" },
    ],
  },
  {
    label: "Cuenta",
    items: [
      { href: "/cuenta/seguridad", Icon: ShieldCheck, title: "Seguridad", desc: "Email, contraseña y datos de la cuenta" },
    ],
  },
];

export default function Cuenta() {
  return (
    <main className="dashboard">
      <BottomNav />
      {GROUPS.map((g) => (
        <section key={g.label} aria-label={g.label}>
          <div className="settings-group">
            {g.items.map((i) => (
              <Link key={i.href} className="settings-item" href={i.href}>
                <span className="settings-icon"><i.Icon size={22} strokeWidth={1.75} aria-hidden="true" /></span>
                <span className="settings-text">
                  <span className="settings-title">{i.title}</span>
                  <span className="settings-desc">{i.desc}</span>
                </span>
                <ChevronRight className="settings-chev" size={18} strokeWidth={1.75} aria-hidden="true" />
              </Link>
            ))}
          </div>
        </section>
      ))}
    </main>
  );
}
