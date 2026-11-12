import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Props = {
  variant?: "primary" | "secondary" | "text" | "danger";
  size?: "md" | "lg";
  fullWidth?: boolean;
  href?: string;
  icon?: ReactNode;
  children: ReactNode;
} & Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children">;

export function Button({
  variant = "primary",
  size = "md",
  fullWidth = false,
  href,
  icon,
  children,
  className = "",
  type = "button",
  ...rest
}: Props) {
  const cls = `ui-btn ${variant} ${size}${fullWidth ? " full" : ""} ${className}`.trim();
  if (href) {
    return (
      <Link className={cls} href={href}>
        {icon}
        {children}
      </Link>
    );
  }
  return (
    <button type={type} className={cls} {...rest}>
      {icon}
      {children}
    </button>
  );
}
