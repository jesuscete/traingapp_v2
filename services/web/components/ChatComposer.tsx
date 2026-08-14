"use client";

import { useEffect, useRef } from "react";

export function ChatComposer({
  placeholder,
  value,
  onChange,
  onSubmit,
  disabled = false,
  hint,
}: {
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  hint?: string;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const wasBusy = useRef(false);

  useEffect(() => {
    if (!disabled) {
      if (wasBusy.current) {
        ref.current?.focus();
      }
      wasBusy.current = false;
    } else {
      wasBusy.current = true;
    }
  }, [disabled]);

  function autoResize() {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!disabled && value.trim()) onSubmit();
    }
  }

  return (
    <div className="chat-composer">
      <textarea
        ref={ref}
        rows={1}
        autoFocus
        placeholder={placeholder}
        value={value}
        onChange={(event) => {
          onChange(event.target.value);
          autoResize();
        }}
        onKeyDown={handleKeyDown}
      />
      <div className="chat-composer-footer">
        <span className="muted chat-composer-hint">
          {hint ?? "Enter para enviar"}
        </span>
        <button
          type="submit"
          className="chat-composer-send"
          disabled={disabled || !value.trim()}
          aria-label="Enviar"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
    </div>
  );
}
