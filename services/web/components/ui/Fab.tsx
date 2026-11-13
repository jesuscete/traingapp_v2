import type { ReactNode } from "react";

type Props = { label: string; icon: ReactNode; onClick?: () => void; variant?: "primary" | "secondary" };

export function Fab({ label, icon, onClick, variant = "primary" }: Props) {
  return (
    <button type="button" className={`ui-fab${variant === "secondary" ? " ui-fab-secondary" : ""}`} aria-label={label} onClick={onClick}>
      {icon}
      <span className="ui-fab-label">{label}</span>
    </button>
  );
}
