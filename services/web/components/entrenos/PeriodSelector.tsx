"use client";

export type PeriodOption = { days: number; label: string };

export const PERIODS: PeriodOption[] = [
  { days: 7, label: "Últimos 7 días" },
  { days: 30, label: "Último mes" },
  { days: 90, label: "3 meses" },
  { days: 180, label: "6 meses" },
  { days: 365, label: "Anual" },
];

export function PeriodSelector({
  value,
  onChange,
}: {
  value: number;
  onChange: (days: number) => void;
}) {
  return (
    <div className="chips" role="tablist" aria-label="Periodo">
      {PERIODS.map((option) => (
        <button
          key={option.days}
          type="button"
          role="tab"
          aria-selected={option.days === value}
          className={`chip chip-toggle${option.days === value ? " on" : ""}`}
          onClick={() => onChange(option.days)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
