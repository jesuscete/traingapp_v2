"use client";

import { useCallback, useState } from "react";

import { Segmented } from "@/components/ui/Segmented";
import { api } from "@/lib/api";
import { BarcodeTab } from "@/components/nutrition/BarcodeTab";
import { AmountPicker, type Amount } from "@/components/nutrition/AmountPicker";
import { FoodForm } from "@/components/nutrition/FoodForm";
import { FreeTextTab } from "@/components/nutrition/FreeTextTab";
import { QuickTab } from "@/components/nutrition/QuickTab";
import { SearchTab } from "@/components/nutrition/SearchTab";
import { Sheet } from "@/components/nutrition/Sheet";
import { TemplatesTab } from "@/components/nutrition/TemplatesTab";
import { errMsg, MEALS } from "@/lib/nutrition";
import type { Food, MealName } from "@/lib/types";

type Tab = "buscar" | "escanear" | "ia" | "rapido" | "platos";

const TABS: { key: Tab; label: string }[] = [
  { key: "buscar", label: "Buscar" },
  { key: "escanear", label: "Escanear" },
  { key: "ia", label: "Texto IA" },
  { key: "rapido", label: "Rápido" },
  { key: "platos", label: "Platos" },
];

type Props = {
  token: string;
  day: string;
  meal: MealName;
  onClose: () => void;
  /** Se llama tras guardar algo para refrescar el día. */
  onChanged: () => void;
};

type Create = { barcode?: string; name?: string } | null;

export function AddFoodSheet({ token, day, meal: initialMeal, onClose, onChanged }: Props) {
  const [tab, setTab] = useState<Tab>("buscar");
  const [meal, setMeal] = useState<MealName>(initialMeal);
  const [food, setFood] = useState<Food | null>(null);
  const [create, setCreate] = useState<Create>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const saved = useCallback(() => {
    onChanged();
    onClose();
  }, [onChanged, onClose]);

  const pick = useCallback((f: Food) => {
    setFood(f);
    setCreate(null);
    setError(null);
    setNotice(null);
  }, []);

  const notFound = useCallback((barcode: string) => {
    setNotice(`Producto no encontrado (${barcode}). Créalo con los datos de la etiqueta.`);
    setCreate({ barcode });
  }, []);

  async function addFood(amount: Amount) {
    if (!food) return;
    setBusy(true);
    setError(null);
    try {
      await api.addMealEntry(
        token,
        amount.kind === "grams"
          ? { eatenOn: day, meal, foodId: food.id, grams: amount.grams }
          : {
              eatenOn: day,
              meal,
              foodId: food.id,
              servings: amount.servings,
              servingLabel: amount.label,
            },
      );
      setNotice(`Añadido: ${food.name}`);
      setFood(null);
      onChanged();
    } catch (err) {
      setError(errMsg(err, "No se pudo añadir"));
    } finally {
      setBusy(false);
    }
  }

  let body: React.ReactNode;
  if (create) {
    body = (
      <FoodForm
        token={token}
        initialBarcode={create.barcode}
        initialName={create.name}
        onCancel={() => setCreate(null)}
        onCreated={pick}
      />
    );
  } else if (food) {
    body = (
      <AmountPicker
        food={food}
        busy={busy}
        error={error}
        onConfirm={addFood}
        onBack={() => setFood(null)}
      />
    );
  } else if (tab === "buscar") {
    body = <SearchTab token={token} onPick={pick} onCreate={(name) => setCreate({ name })} />;
  } else if (tab === "escanear") {
    body = <BarcodeTab token={token} onFound={pick} onNotFound={notFound} />;
  } else if (tab === "ia") {
    body = <FreeTextTab token={token} day={day} meal={meal} onSaved={saved} />;
  } else if (tab === "rapido") {
    body = <QuickTab token={token} day={day} meal={meal} onSaved={saved} />;
  } else {
    body = <TemplatesTab token={token} day={day} meal={meal} onApplied={saved} />;
  }

  return (
    <Sheet title="Añadir comida" onClose={onClose}>
      <div className="nu-sheet-top">
        <label className="nu-meal-pick">
          <span className="muted">Añadir a</span>
          <select value={meal} onChange={(e) => setMeal(e.target.value as MealName)}>
            {MEALS.map((m) => (
              <option key={m.key} value={m.key}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
        <Segmented
          items={TABS.map((t) => ({ id: t.key, label: t.label }))}
          value={tab}
          label="Cómo añadir"
          onChange={(id) => {
            setTab(id);
            setFood(null);
            setCreate(null);
            setError(null);
          }}
        />
      </div>
      {notice && <p className="ok nu-notice">{notice}</p>}
      {body}
    </Sheet>
  );
}
