import type { ReactNode } from "react";

import { Button } from "./Button";

type Props = {
  icon: ReactNode;
  title: string;
  text?: string;
  action?: { label: string; href?: string; onClick?: () => void };
};

export function EmptyState({ icon, title, text, action }: Props) {
  return (
    <div className="ui-empty">
      <span className="ui-empty-icon" aria-hidden="true">
        {icon}
      </span>
      <strong>{title}</strong>
      {text && <p>{text}</p>}
      {action && (
        <Button href={action.href} onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}
