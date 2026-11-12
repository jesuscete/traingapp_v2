import { translateDiscipline } from "@/lib/labels";
import { formatDuration } from "@/lib/format";
import { toISODate } from "@/lib/nutrition";
import type { HomeSummary } from "@/lib/types";

const DAY_LETTERS = ["D", "L", "M", "X", "J", "V", "S"];

function lastSevenDays(): string[] {
  const out: string[] = [];
  const now = new Date();
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i);
    out.push(toISODate(d));
  }
  return out;
}

export function WeekCard({ home, showDays = true }: { home: HomeSummary; showDays?: boolean }) {
  const max = Math.max(1, ...home.weekBySport.map((s) => s.minutes));
  const delta =
    home.prevWeekMinutes > 0
      ? Math.round(((home.weekMinutes - home.prevWeekMinutes) / home.prevWeekMinutes) * 100)
      : null;
  const active = new Set(home.activeDays);

  return (
    <>
      <div className="hm-totals">
        <span>
          <b>{home.weekSessions}</b> {home.weekSessions === 1 ? "sesión" : "sesiones"}
        </span>
        <span>
          <b>{formatDuration(home.weekMinutes)}</b>
        </span>
        {delta != null && (
          <span className={delta >= 0 ? "hm-up" : "hm-down"}>
            {delta >= 0 ? "↑" : "↓"} {Math.abs(delta)}% vs semana anterior
          </span>
        )}
      </div>
      {home.weekBySport.map((s) => (
        <div key={s.discipline} className="hm-sport">
          <span>{translateDiscipline(s.discipline)}</span>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${(s.minutes / max) * 100}%` }} />
          </div>
          <span className="muted">{Math.round(s.minutes)} min</span>
        </div>
      ))}
      {home.weekBySport.length === 0 && <p className="muted">Aún sin actividad esta semana.</p>}
      {showDays && (
        <div className="hm-days">
          {lastSevenDays().map((iso) => {
            const [y, m, d] = iso.split("-").map(Number);
            return (
              <div key={iso} className="hm-day">
                <span className={`hm-dot${active.has(iso) ? " on" : ""}`} />
                {DAY_LETTERS[new Date(y, m - 1, d).getDay()]}
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
