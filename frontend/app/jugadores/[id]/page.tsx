"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type PlayerClub = { id: number; name: string; membership_type: string; is_current: boolean };
type Player = {
  id: number;
  display_name: string;
  full_name: string | null;
  image_url: string | null;
  date_of_birth: string | null;
  place_of_birth: string | null;
  country_of_birth: string | null;
  height_cm: number | null;
  preferred_foot: string;
  career_status: string;
  position: string | null;
  citizenships: string[];
  current_clubs: PlayerClub[];
  latest_market_value: number | null;
  data_as_of: string | null;
};
type Performance = {
  season: string;
  club: string;
  competition: string;
  appearances: number | null;
  goals: number | null;
  assists: number | null;
  minutes_played: number | null;
  yellow_cards: number | null;
  red_cards: number | null;
};
type MarketValue = { valued_on: string; amount: number; currency_code: string | null };
type Transfer = {
  transfer_date: string | null;
  season: string | null;
  from_team: string;
  to_team: string;
  transfer_type: string;
  market_value_amount: number | null;
  fee_amount: number | null;
  currency_code: string | null;
};
type Injury = {
  season: string | null;
  reason: string;
  started_on: string | null;
  ended_on: string | null;
  days_missed: number | null;
  games_missed: number | null;
};
type Section = "RENDIMIENTO" | "VALOR" | "TRANSFERENCIAS" | "LESIONES";

const positionLabels: Record<string, string> = {
  Goalkeeper: "Arquero",
  "Centre-Back": "Defensor central",
  "Left-Back": "Lateral izquierdo",
  "Right-Back": "Lateral derecho",
  "Defensive Midfield": "Mediocampista defensivo",
  "Central Midfield": "Mediocampista central",
  "Attacking Midfield": "Mediocampista ofensivo",
  "Left Winger": "Extremo izquierdo",
  "Right Winger": "Extremo derecho",
  "Centre-Forward": "Delantero centro",
  "Second Striker": "Segundo delantero",
};
const countryLabels: Record<string, string> = {
  Italy: "Italia",
  Spain: "España",
  Ukraine: "Ucrania",
  "United States": "Estados Unidos",
};
const footLabels: Record<string, string> = { RIGHT: "Derecha", LEFT: "Izquierda", BOTH: "Ambas" };
const statusLabels: Record<string, string> = { ACTIVE: "En actividad", RETIRED: "Retirado", DECEASED: "Fallecido" };
const transferLabels: Record<string, string> = {
  TRANSFER: "Transferencia",
  LOAN: "Préstamo",
  LOAN_RETURN: "Fin del préstamo",
  FREE_TRANSFER: "Libre",
  RETIRED: "Retiro",
};
const injuryLabels: Record<string, string> = {
  "stomach problems": "Problemas estomacales",
  "muscle injury": "Lesión muscular",
  "hamstring injury": "Lesión en los isquiotibiales",
  "knee injury": "Lesión de rodilla",
  "ankle injury": "Lesión de tobillo",
  "unknown injury": "Lesión sin especificar",
};
const sections: Array<{ value: Section; label: string }> = [
  { value: "RENDIMIENTO", label: "Rendimiento" },
  { value: "VALOR", label: "Valor de mercado" },
  { value: "TRANSFERENCIAS", label: "Transferencias" },
  { value: "LESIONES", label: "Lesiones" },
];

const moneyFormatter = new Intl.NumberFormat("es-AR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const numberFormatter = new Intl.NumberFormat("es-AR");
const dateFormatter = new Intl.DateTimeFormat("es-AR", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" });

function translatePosition(value: string | null) { return value ? positionLabels[value] ?? value : "Posición sin informar"; }
function translateCountry(value: string) { return countryLabels[value] ?? value; }
function translateInjury(value: string) { return injuryLabels[value.toLowerCase()] ?? value; }
function formatMoney(value: number | null) { return value === null ? "Sin informar" : moneyFormatter.format(value); }
function formatDate(value: string | null) { return value ? dateFormatter.format(new Date(`${value}T00:00:00`)) : "Sin fecha"; }
function formatCount(value: number | null, singular: string, plural: string) {
  const count = value ?? 0;
  return `${count} ${count === 1 ? singular : plural}`;
}
function calculateAge(value: string | null) {
  if (!value) return null;
  const birth = new Date(`${value}T00:00:00`);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  if (today.getMonth() < birth.getMonth() || (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate())) age -= 1;
  return age;
}

export default function PlayerPage() {
  const params = useParams();
  const rawId = params.id;
  const playerId = Number(Array.isArray(rawId) ? rawId[0] : rawId);
  const [player, setPlayer] = useState<Player | null>(null);
  const [performances, setPerformances] = useState<Performance[]>([]);
  const [marketValues, setMarketValues] = useState<MarketValue[]>([]);
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [injuries, setInjuries] = useState<Injury[]>([]);
  const [section, setSection] = useState<Section>("RENDIMIENTO");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isInteger(playerId) || playerId <= 0) {
      setError("El jugador solicitado no es válido.");
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    async function load() {
      try {
        const paths = ["", "/performances", "/market-values", "/transfers", "/injuries"];
        const responses = await Promise.all(paths.map((path) => fetch(`${API_URL}/api/v1/players/${playerId}${path}`, { signal: controller.signal })));
        if (responses.some((response) => !response.ok)) throw new Error();
        const [profile, performanceData, valueData, transferData, injuryData] = await Promise.all(responses.map((response) => response.json()));
        setPlayer(profile as Player);
        setPerformances(performanceData as Performance[]);
        setMarketValues(valueData as MarketValue[]);
        setTransfers(transferData as Transfer[]);
        setInjuries(injuryData as Injury[]);
      } catch (reason) {
        if (!(reason instanceof DOMException && reason.name === "AbortError")) setError("No pudimos cargar la ficha del jugador.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [playerId]);

  const totals = useMemo(() => performances.reduce((result, item) => ({
    appearances: result.appearances + (item.appearances ?? 0),
    goals: result.goals + (item.goals ?? 0),
    assists: result.assists + (item.assists ?? 0),
    minutes: result.minutes + (item.minutes_played ?? 0),
  }), { appearances: 0, goals: 0, assists: 0, minutes: 0 }), [performances]);
  const maxMarketValue = Math.max(...marketValues.map((item) => item.amount), 1);
  const age = calculateAge(player?.date_of_birth ?? null);

  return (
    <main className="player-page">
      <header className="site-header">
        <a className="brand" href="/" aria-label="PlayerHub, inicio"><span className="brand-mark">PH</span><span>PlayerHub</span></a>
        <nav aria-label="Navegación principal"><a href="/">Clubes</a><a href="#historial">Historial</a><span className="language-badge">ES</span></nav>
      </header>

      {loading ? (
        <div className="player-loading" role="status"><span className="loader" /><p>Preparando la ficha del jugador…</p></div>
      ) : error || !player ? (
        <div className="player-loading"><span className="empty-mark">!</span><h1>No pudimos abrir esta ficha</h1><p>{error}</p><a className="primary-link" href="/">Volver a clubes</a></div>
      ) : (
        <>
          <section className="profile-hero">
            <div className="profile-inner">
              <a className="back-link" href={player.current_clubs[0] ? `/clubes/${player.current_clubs[0].id}` : "/"}>← Volver al plantel</a>
              <div className="profile-layout">
                <div className="profile-photo">
                  {player.image_url ? <img src={player.image_url} alt={`Foto de ${player.display_name}`} /> : <span>{player.display_name.slice(0, 2)}</span>}
                </div>
                <div className="profile-copy">
                  <div className="profile-tags"><span>{translatePosition(player.position)}</span><span className="career-tag">{statusLabels[player.career_status] ?? player.career_status}</span></div>
                  <h1>{player.display_name}</h1>
                  <p className="full-name">{player.full_name ?? player.display_name}</p>
                  <div className="current-clubs">
                    {player.current_clubs.map((club) => <a href={`/clubes/${club.id}`} key={club.id}>{club.name}{club.membership_type === "LOAN" ? " · A préstamo" : ""}</a>)}
                  </div>
                </div>
                <div className="profile-value"><span>Valor de mercado</span><strong>{formatMoney(player.latest_market_value)}</strong><small>Última cotización registrada</small></div>
              </div>
            </div>
          </section>

          <section className="player-content">
            <div className="bio-grid">
              <article><span>Edad</span><strong>{age !== null ? `${age} años` : "Sin informar"}</strong><small>{formatDate(player.date_of_birth)}</small></article>
              <article><span>Altura</span><strong>{player.height_cm ? `${player.height_cm} cm` : "Sin informar"}</strong><small>{player.place_of_birth ?? "Lugar sin informar"}</small></article>
              <article><span>Pie hábil</span><strong>{footLabels[player.preferred_foot] ?? player.preferred_foot}</strong><small>{translateCountry(player.country_of_birth ?? "País sin informar")}</small></article>
              <article><span>Nacionalidad</span><strong>{player.citizenships.map(translateCountry).join(" · ")}</strong><small>Datos personales</small></article>
            </div>

            <div className="career-highlights">
              <div><span>Partidos registrados</span><strong>{numberFormatter.format(totals.appearances)}</strong></div>
              <div><span>Goles</span><strong>{numberFormatter.format(totals.goals)}</strong></div>
              <div><span>Asistencias</span><strong>{numberFormatter.format(totals.assists)}</strong></div>
              <div><span>Minutos informados</span><strong>{numberFormatter.format(totals.minutes)}</strong></div>
            </div>

            <section className="history-section" id="historial">
              <div className="history-heading"><div><span className="section-label">Carrera</span><h2>Historial del jugador</h2></div><span>Datos al {formatDate(player.data_as_of)}</span></div>
              <div className="history-tabs" role="tablist" aria-label="Información histórica del jugador">
                {sections.map((item) => <button key={item.value} type="button" role="tab" aria-selected={section === item.value} className={section === item.value ? "active" : ""} onClick={() => setSection(item.value)}>{item.label}</button>)}
              </div>

              {section === "RENDIMIENTO" && (
                <div className="data-panel"><div className="table-wrap"><table><thead><tr><th>Temporada</th><th>Club</th><th>Competencia</th><th>Partidos</th><th>Goles</th><th>Asistencias</th><th>Tarjetas</th></tr></thead><tbody>
                  {performances.slice(0, 14).map((item, index) => <tr key={`${item.season}-${item.club}-${item.competition}-${index}`}><td>{item.season}</td><td>{item.club}</td><td>{item.competition}</td><td>{item.appearances ?? "—"}</td><td>{item.goals ?? "—"}</td><td>{item.assists ?? "—"}</td><td><span className="card-count yellow">{item.yellow_cards ?? 0}</span><span className="card-count red">{item.red_cards ?? 0}</span></td></tr>)}
                </tbody></table></div></div>
              )}

              {section === "VALOR" && (
                <div className="data-panel value-history"><div className="chart-summary"><span>Evolución histórica</span><strong>{marketValues.length} cotizaciones</strong></div>
                  {marketValues.length ? <div className="value-chart" aria-label="Evolución del valor de mercado">{marketValues.map((item) => <div className="value-column" key={item.valued_on} title={`${formatDate(item.valued_on)}: ${formatMoney(item.amount)}`}><span className="value-label">{item.amount === maxMarketValue ? formatMoney(item.amount) : ""}</span><i style={{ height: `${Math.max(7, (item.amount / maxMarketValue) * 100)}%` }} /><small>{new Date(`${item.valued_on}T00:00:00`).getUTCFullYear()}</small></div>)}</div> : <p className="empty-state">No hay valores registrados.</p>}
                </div>
              )}

              {section === "TRANSFERENCIAS" && (
                <div className="data-panel timeline">{transfers.length ? transfers.map((item, index) => <article key={`${item.transfer_date}-${index}`}><div className="timeline-date"><strong>{formatDate(item.transfer_date)}</strong><span>{item.season ?? "Temporada sin informar"}</span></div><div className="timeline-route"><span>{item.from_team}</span><b>→</b><span>{item.to_team}</span></div><div className="timeline-fee"><span>{transferLabels[item.transfer_type] ?? item.transfer_type}</span><strong>{item.fee_amount ? formatMoney(item.fee_amount) : "Sin cargo informado"}</strong></div></article>) : <p className="empty-state">No hay transferencias registradas.</p>}</div>
              )}

              {section === "LESIONES" && (
                <div className="data-panel injuries-list">{injuries.length ? injuries.map((item, index) => <article key={`${item.started_on}-${index}`}><div className="injury-icon">+</div><div><span>{item.season ?? "Temporada sin informar"}</span><h3>{translateInjury(item.reason)}</h3><p>{formatDate(item.started_on)} — {formatDate(item.ended_on)}</p></div><div className="injury-impact"><strong>{formatCount(item.days_missed, "día", "días")}</strong><span>{formatCount(item.games_missed, "partido ausente", "partidos ausentes")}</span></div></article>) : <p className="empty-state success-state">No hay lesiones registradas para este jugador.</p>}</div>
              )}
            </section>
          </section>

          <footer><a className="brand footer-brand" href="/"><span className="brand-mark">PH</span><span>PlayerHub</span></a><p>Información futbolística clara, propia y trazable.</p><span>Versión piloto · Argentina</span></footer>
        </>
      )}
    </main>
  );
}
