type Props = { height?: number | string; width?: number | string; className?: string };

export function Skeleton({ height = 16, width = "100%", className = "" }: Props) {
  return <div className={`ui-skeleton ${className}`.trim()} style={{ height, width }} aria-hidden="true" />;
}
