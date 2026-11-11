"use client";

import { useEffect, useState } from "react";

/** Alterna los fotogramas (inicio/fin) cada ~800 ms; tocar pausa/reanuda. */
export function ExerciseAnimation({ urls, alt }: { urls: string[]; alt: string }) {
  const [frame, setFrame] = useState(0);
  const [paused, setPaused] = useState(false);
  const [reduced, setReduced] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const multi = urls.length > 1;
  useEffect(() => {
    if (!multi || paused || reduced) return;
    const id = window.setInterval(() => setFrame((f) => (f + 1) % urls.length), 800);
    return () => window.clearInterval(id);
  }, [multi, paused, reduced, urls.length]);

  if (urls.length === 0 || failed) {
    return <div className="ex-anim ex-anim-empty muted">Sin imagen</div>;
  }

  return (
    <button
      type="button"
      className="ex-anim"
      onClick={() => {
        if (reduced) setFrame((f) => (f + 1) % urls.length);
        else setPaused((p) => !p);
      }}
      aria-label={
        reduced ? "Cambiar de imagen" : paused ? "Reanudar animación" : "Pausar animación"
      }
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={urls[frame % urls.length]}
        alt={alt}
        decoding="async"
        onError={() => setFailed(true)}
      />
      {multi && (
        <span className="ex-anim-badge">
          {reduced ? `${frame + 1}/${urls.length}` : paused ? "Pausado" : "▶"}
        </span>
      )}
    </button>
  );
}
