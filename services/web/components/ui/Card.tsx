import Link from "next/link";
import type { ReactNode } from "react";

type Props = {
  title?: string;
  action?: { label: string; href: string };
  variant?: "default" | "raised";
  className?: string;
  children: ReactNode;
};

export function Card({ title, action, variant = "default", className = "", children }: Props) {
  return (
    <section className={`ui-card ${variant === "raised" ? "raised" : ""} ${className}`.trim()}>
      {(title || action) && (
        <header className="ui-card-head">
          {title && <h2 className="ui-card-title">{title}</h2>}
          {action && (
            <Link className="ui-card-action" href={action.href}>
              {action.label}
            </Link>
          )}
        </header>
      )}
      {children}
    </section>
  );
}
