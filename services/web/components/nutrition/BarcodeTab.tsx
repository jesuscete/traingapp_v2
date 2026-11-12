"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { errMsg } from "@/lib/nutrition";
import type { Food } from "@/lib/types";

type DetectedBarcode = { rawValue: string };
type BarcodeDetectorLike = {
  detect: (source: HTMLVideoElement) => Promise<DetectedBarcode[]>;
};
type BarcodeDetectorCtor = new (options?: { formats?: string[] }) => BarcodeDetectorLike;

function getDetectorCtor(): BarcodeDetectorCtor | null {
  if (typeof window === "undefined") return null;
  const ctor = (window as unknown as { BarcodeDetector?: BarcodeDetectorCtor }).BarcodeDetector;
  return ctor ?? null;
}

function cameraAvailable(): boolean {
  return (
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof window !== "undefined" &&
    window.isSecureContext
  );
}

type Props = {
  token: string;
  onFound: (food: Food) => void;
  onNotFound: (barcode: string) => void;
};

export function BarcodeTab({ token, onFound, onNotFound }: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<number | null>(null);
  const [supported, setSupported] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [manual, setManual] = useState("");
  const [looking, setLooking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSupported(getDetectorCtor() !== null && cameraAvailable());
  }, []);

  const stopCamera = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setScanning(false);
  }, []);

  useEffect(() => stopCamera, [stopCamera]);

  const lookup = useCallback(
    async (digits: string) => {
      const code = digits.replace(/\D/g, "");
      if (code.length < 6) {
        setError("Código de barras no válido.");
        return;
      }
      setLooking(true);
      setError(null);
      try {
        const food = await api.getFoodByBarcode(token, code);
        onFound(food);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          onNotFound(code);
        } else if (err instanceof ApiError && err.status === 503) {
          setError("Open Food Facts no responde ahora. Inténtalo luego o crea el alimento a mano.");
        } else {
          setError(errMsg(err, "No se pudo buscar el producto"));
        }
      } finally {
        setLooking(false);
      }
    },
    [token, onFound, onNotFound],
  );

  async function startCamera() {
    const Ctor = getDetectorCtor();
    if (!Ctor) return;
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      streamRef.current = stream;
      setScanning(true);
      const video = videoRef.current;
      if (!video) return;
      video.srcObject = stream;
      await video.play();
      const detector = new Ctor({ formats: ["ean_13", "ean_8", "upc_a", "upc_e"] });
      let busy = false;
      timerRef.current = window.setInterval(async () => {
        if (busy || video.readyState < 2) return;
        busy = true;
        try {
          const codes = await detector.detect(video);
          if (codes.length > 0 && codes[0].rawValue) {
            stopCamera();
            void lookup(codes[0].rawValue);
          }
        } catch {
          // fotograma sin código legible: se reintenta en el siguiente ciclo
        } finally {
          busy = false;
        }
      }, 300);
    } catch (err) {
      stopCamera();
      setError(errMsg(err, "No se pudo abrir la cámara. Revisa los permisos."));
    }
  }

  return (
    <div className="nu-form">
      {supported ? (
        <>
          <div className={`nu-scan${scanning ? " on" : ""}`}>
            <video ref={videoRef} playsInline muted />
            {!scanning && <span className="muted">Apunta al código de barras del envase</span>}
          </div>
          {scanning ? (
            <button type="button" className="secondary" onClick={stopCamera}>
              Detener cámara
            </button>
          ) : (
            <button type="button" className="wk-primary" disabled={looking} onClick={startCamera}>
              Activar cámara
            </button>
          )}
        </>
      ) : (
        <p className="nu-warn">
          La cámara necesita HTTPS (dev-up.ps1 -Https) y un navegador compatible. Mientras, escribe el código a
          mano.
        </p>
      )}

      <form
        className="nu-manual"
        onSubmit={(e) => {
          e.preventDefault();
          void lookup(manual);
        }}
      >
        <label className="nu-field">
          <span>Código de barras (manual)</span>
          <input
            type="text"
            inputMode="numeric"
            placeholder="8410000000000"
            value={manual}
            onChange={(e) => setManual(e.target.value.replace(/\D/g, ""))}
          />
        </label>
        <button type="submit" disabled={looking || manual.length < 6}>
          {looking ? "Buscando…" : "Buscar producto"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
