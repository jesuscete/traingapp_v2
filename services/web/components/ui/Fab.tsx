import type { ReactNode } from "react";

type Props = { label: string; icon: ReactNode; onClick?: () => void };

export function Fab({ label, icon, onClick }: Props) {
  return (
    <button type="button" className="ui-fab" aria-label={label} onClick={onClick}>
      {icon}
      <span className="ui-fab-label">{label}</span>
    </button>
  );
}
