"use client";

import { useState } from "react";

export function ExerciseThumb({
  src,
  alt = "",
  size = 52,
}: {
  src: string | null | undefined;
  alt?: string;
  size?: number;
}) {
  const [failed, setFailed] = useState(false);
  return (
    <span className="ex-thumb" style={{ width: size, height: size }}>
      {src && !failed ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt={alt} loading="lazy" decoding="async" onError={() => setFailed(true)} />
      ) : (
        <svg viewBox="0 0 24 24" width="55%" height="55%" aria-hidden="true">
          <path
            d="M3 9v6M6 7v10M18 7v10M21 9v6M6 12h12"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            fill="none"
          />
        </svg>
      )}
    </span>
  );
}
