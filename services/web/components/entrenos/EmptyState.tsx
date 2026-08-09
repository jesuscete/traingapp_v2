export function EmptyState({
  message,
  hint,
}: {
  message: string;
  hint?: string;
}) {
  return (
    <div className="block">
      <p>{message}</p>
      {hint && <p className="muted">{hint}</p>}
    </div>
  );
}
