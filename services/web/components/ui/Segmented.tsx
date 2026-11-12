"use client";

import type { ReactNode } from "react";

export type SegmentItem<T extends string = string> = { id: T; label: string; icon?: ReactNode };

type Props<T extends string> = {
  items: SegmentItem<T>[];
  value: T;
  onChange: (id: T) => void;
  label?: string;
};

export function Segmented<T extends string>({ items, value, onChange, label }: Props<T>) {
  function onKey(e: React.KeyboardEvent, index: number) {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault();
    const next = (index + (e.key === "ArrowRight" ? 1 : items.length - 1)) % items.length;
    onChange(items[next].id);
    (e.currentTarget.parentElement?.children[next] as HTMLElement | undefined)?.focus();
  }
  return (
    <div className="seg-tabs" role="tablist" aria-label={label}>
      {items.map((item, i) => {
        const selected = item.id === value;
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            id={`seg-${item.id}`}
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            className="seg-tab"
            onClick={() => onChange(item.id)}
            onKeyDown={(e) => onKey(e, i)}
          >
            {item.icon}
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
