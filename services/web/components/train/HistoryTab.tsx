"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { DisciplineBreakdown } from "@/components/entrenos/DisciplineBreakdown";
import { EmptyState } from "@/components/entrenos/EmptyState";
import { EmptyState as UiEmpty } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { ClipboardList } from "lucide-react";
import { HighlightsStats } from "@/components/entrenos/HighlightsStats";
import { PeriodSelector } from "@/components/entrenos/PeriodSelector";
import { ProgressionCard } from "@/components/entrenos/ProgressionCard";
import { RecentSessions } from "@/components/entrenos/RecentSessions";
import { SessionTable } from "@/components/entrenos/SessionTable";
import { SessionDetail } from "@/components/train/SessionDetail";
import { api } from "@/lib/api";
import { useIsExpanded } from "@/lib/useMediaQuery";
import { formatDuration, formatKcal } from "@/lib/format";
import { translateDiscipline } from "@/lib/labels";
import type { DisciplineStat, HistorySummary, SessionPage } from "@/lib/types";

const TOKEN_KEY = "traingapp_token";
const PAGE_SIZE = 20;

export function HistoryTab() {
  return (
    <Suspense fallback={<Skeleton height={160} />}>
      <EntrenosInner />
    </Suspense>
  );
}

function EntrenosInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const view = searchParams.get("view") === "todos" ? "todos" : "resumen";
  const expanded = useIsExpanded();
  const selectedId = searchParams.get("id");
  const select = expanded
    ? (id: string) => {
        const next = new URLSearchParams(searchParams.toString());
        next.set("id", id);
        router.replace(`${pathname}?${next.toString()}`, { scroll: false });
      }
    : undefined;

  const [token, setToken] = useState<string | null>(null);
  const [summary, setSummary] = useState<HistorySummary | null>(null);
  const [pageData, setPageData] = useState<SessionPage | null>(null);
  const [period, setPeriod] = useState(30);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [disciplines, setDisciplines] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const availableDisciplines = useMemo(
    () =>
      Array.from(
        new Set([
          ...(summary?.byDiscipline.map((d: DisciplineStat) => d.discipline) ??
            []),
          ...(pageData?.items.map((s) => s.discipline) ?? []),
        ]),
      ).sort(),
    [summary, pageData],
  );

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      router.replace("/");
      return;
    }
    setToken(stored);
  }, [router]);

  const loadSummary = useCallback(
    async (accessToken: string, days: number) => {
      setLoading(true);
      try {
        const data = await api.getSessionsSummary(accessToken, days);
        setSummary(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al cargar datos");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const loadPage = useCallback(
    async (accessToken: string, params: { page: number; q: string; disciplines: string[] }) => {
      setLoading(true);
      try {
        const data = await api.listSessions(accessToken, {
          page: params.page,
          pageSize: PAGE_SIZE,
          q: params.q || undefined,
          discipline: params.disciplines,
        });
        setPageData(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al cargar datos");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (!token) return;
    if (view === "todos") {
      loadPage(token, { page, q, disciplines });
    } else {
      loadSummary(token, period);
    }
  }, [token, view, period, page, q, disciplines, loadPage, loadSummary]);

  const onSearch = (value: string) => {
    setQ(value);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => setPage(1), 300);
  };

  const toggleDiscipline = (discipline: string) => {
    setDisciplines((prev) =>
      prev.includes(discipline)
        ? prev.filter((d) => d !== discipline)
        : [...prev, discipline],
    );
    setPage(1);
  };

  const totalPages = pageData ? Math.ceil(pageData.total / pageData.pageSize) : 0;

  const list = (
    <div className="tab-body">

      <p className="muted">
        {view === "todos"
          ? pageData
            ? `${pageData.total} ${pageData.total === 1 ? "entrenamiento" : "entrenamientos"}`
            : " "
          : "Resumen por periodo y detalle por actividad"}
      </p>

      {error && (
        <p className="error">
          {error}{" "}
          <button
            type="button"
            className="ui-btn text"
            onClick={() => token && (view === "todos" ? void loadPage(token, { page, q, disciplines }) : void loadSummary(token, period))}
          >
            Reintentar
          </button>
        </p>
      )}

      {view === "todos" ? (
        <section className="block">
          <div className="filters-row">
            <input
              type="search"
              placeholder="Buscar entrenamiento..."
              value={q}
              onChange={(e) => onSearch(e.target.value)}
              className="search-input"
            />
            <div className="chips">
              {availableDisciplines.map((discipline) => (
                <button
                  key={discipline}
                  type="button"
                  aria-pressed={disciplines.includes(discipline)}
                  className={`chip chip-toggle${disciplines.includes(discipline) ? " on" : ""}`}
                  onClick={() => toggleDiscipline(discipline)}
                >
                  {translateDiscipline(discipline)}
                </button>
              ))}
            </div>
          </div>

          {loading ? (
            <Skeleton height={160} />
          ) : !pageData || pageData.items.length === 0 ? (
            <UiEmpty
              icon={<ClipboardList size={28} strokeWidth={1.75} />}
              title={q || disciplines.length > 0 ? "Sin resultados" : "Registra tu primer entreno"}
              text={q || disciplines.length > 0 ? "Prueba con otro filtro." : "Aparecerá aquí en cuanto lo guardes."}
              action={q || disciplines.length > 0 ? undefined : { label: "Empezar entreno", href: "/entrenar" }}
            />
          ) : (
            <>
              <SessionTable sessions={pageData.items} onSelect={select} selectedId={selectedId} />
              {totalPages > 1 && (
                <div className="pagination">
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={page <= 1 || loading}
                    onClick={() => setPage(page - 1)}
                  >
                    Anterior
                  </button>
                  <span className="muted">
                    Página {page} de {totalPages}
                  </span>
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={!pageData.hasMore || loading}
                    onClick={() => setPage(page + 1)}
                  >
                    Siguiente
                  </button>
                </div>
              )}
            </>
          )}
        </section>
      ) : loading && !summary ? (
        <div className="stack"><Skeleton height={64} /><Skeleton height={160} /><Skeleton height={120} /></div>
      ) : summary ? (
        <>
          <PeriodSelector value={period} onChange={setPeriod} />

          {loading && <Skeleton height={4} />}

          <HighlightsStats highlights={summary.highlights} />

          <div className="breakdown-grid">
            <DisciplineBreakdown
              title="Tiempo por actividad"
              rows={summary.byDiscipline
                .map((d) => ({
                  label: translateDiscipline(d.discipline),
                  value: formatDuration(d.durationMinutes),
                }))
                .filter((row) => row.value !== "—")}
              empty="Sin tiempo registrado en este periodo."
            />
            <DisciplineBreakdown
              title="Calorías por actividad"
              rows={summary.byDiscipline
                .map((d) => ({
                  label: translateDiscipline(d.discipline),
                  value: formatKcal(d.estimatedKcal),
                }))
                .filter((row) => row.value !== "—")}
              empty="Sin calorías registradas en este periodo."
            />
          </div>

          <ProgressionCard deltas={summary.deltas} />

          <RecentSessions
            sessions={summary.recent}
            totalInPeriod={summary.highlights.totalSessions}
            onSelect={select}
            selectedId={selectedId}
          />
        </>
      ) : (
        <EmptyState
          message="No hay datos en este periodo."
          hint="Cambia el periodo o registra entrenos desde el chat de Inicio."
        />
      )}
    </div>
  );

  if (!expanded) return list;
  return (
    <div className="split">
      <div className="split-list">{list}</div>
      <div className="split-detail">
        {selectedId ? (
          <SessionDetail key={selectedId} id={selectedId} embedded />
        ) : (
          <UiEmpty
            icon={<ClipboardList size={28} strokeWidth={1.75} />}
            title="Selecciona un entreno"
            text="Elige uno de la lista para ver su detalle."
          />
        )}
      </div>
    </div>
  );
}

