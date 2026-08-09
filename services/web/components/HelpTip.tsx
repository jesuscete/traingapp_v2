export function HelpTip({ children, tip }: { children: React.ReactNode; tip: string }) {
  return (
    <span className="helptip" data-tip={tip}>
      {children}
    </span>
  );
}
