"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import ClubView, { type ClubDetail, type ClubSummary, type SquadMember } from "./components/club-view";
import { translateCountry } from "./lib/translations";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type PlatformStats = {
  clubs: number;
  players: number;
  performances: number;
  market_values: number;
  transfers: number;
  injuries: number;
  data_as_of: string | null;
};

const numberFormatter = new Intl.NumberFormat("es-AR");

export default function Home() {
  const [query, setQuery] = useState("Independiente");
  const [results, setResults] = useState<ClubSummary[]>([]);
  const [club, setClub] = useState<ClubDetail | null>(null);
  const [squad, setSquad] = useState<SquadMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [platformStats, setPlatformStats] = useState<PlatformStats | null>(null);

  const loadClub = useCallback(async (selected: ClubSummary) => {
    setLoading(true);
    setError(null);
    setResults([]);
    try {
      const [detailResponse, squadResponse] = await Promise.all([
        fetch(`${API_URL}/api/v1/clubs/${selected.id}`),
        fetch(`${API_URL}/api/v1/clubs/${selected.id}/squad`),
      ]);
      if (!detailResponse.ok || !squadResponse.ok) throw new Error();
      const [detail, members] = await Promise.all([
        detailResponse.json() as Promise<ClubDetail>,
        squadResponse.json() as Promise<SquadMember[]>,
      ]);
      setClub(detail);
      setSquad(members);
    } catch {
      setError("No pudimos conectarnos con PlayerHub. Comprobá que la API esté encendida.");
    } finally {
      setLoading(false);
    }
  }, []);

  const searchClubs = useCallback(async (term: string, chooseFirst = false) => {
    if (term.trim().length < 2) return;
    setSearching(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/v1/clubs?search=${encodeURIComponent(term.trim())}`);
      if (!response.ok) throw new Error();
      const clubs = (await response.json()) as ClubSummary[];
      if (chooseFirst) {
        const target = clubs.find((item) => item.is_complete) ?? clubs[0];
        if (target) await loadClub(target);
        else {
          setLoading(false);
          setError("No encontramos clubes con ese nombre.");
        }
      } else {
        setResults(clubs);
        if (clubs.length === 0) setError("No encontramos clubes con ese nombre.");
      }
    } catch {
      setLoading(false);
      setError("No pudimos realizar la búsqueda. Intentá nuevamente.");
    } finally {
      setSearching(false);
    }
  }, [loadClub]);

  useEffect(() => {
    const controller = new AbortController();
    void searchClubs("Independiente", true);
    void fetch(`${API_URL}/api/v1/stats`, { signal: controller.signal })
      .then((response) => response.ok ? response.json() : null)
      .then((stats) => { if (stats) setPlatformStats(stats as PlatformStats); })
      .catch(() => undefined);
    return () => controller.abort();
  }, [searchClubs]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void searchClubs(query);
  }

  return (
    <main>
      <header className="site-header">
        <a className="brand" href="#inicio" aria-label="PlayerHub, inicio">
          <span className="brand-mark">PH</span><span>PlayerHub</span>
        </a>
        <nav aria-label="Navegación principal">
          <a href="/clubes">Clubes</a><a href="/jugadores">Jugadores</a><span className="language-badge">ES</span>
        </nav>
      </header>

      <section className="hero" id="inicio">
        <div className="hero-copy">
          <span className="eyebrow">Datos de fútbol, en un solo lugar</span>
          <h1>El fútbol, jugador por jugador.</h1>
          <p>Explorá planteles, préstamos, trayectorias y valores de mercado con información organizada por PlayerHub.</p>
          <a className="catalog-link" href="/clubes">Explorar todos los clubes argentinos →</a>
          <form className="search" onSubmit={handleSubmit} role="search">
            <span className="search-icon" aria-hidden="true">⌕</span>
            <label className="sr-only" htmlFor="club-search">Buscar un club</label>
            <input id="club-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscá un club, por ejemplo Independiente" minLength={2} />
            <button type="submit" disabled={searching || query.trim().length < 2}>{searching ? "Buscando…" : "Buscar"}</button>
          </form>
          {results.length > 0 && (
            <div className="search-results" aria-label="Resultados de búsqueda">
              {results.map((result) => (
                <a key={result.id} href={`/clubes/${result.id}`}>
                  <span>{result.name}</span><small>{translateCountry(result.country ?? "País sin informar")}</small>
                </a>
              ))}
            </div>
          )}
        </div>
        <div className="hero-card" aria-label="Cobertura actual de PlayerHub">
          <span className="hero-card-kicker">COBERTURA ACTUAL</span><strong>{platformStats ? numberFormatter.format(platformStats.players) : "—"}</strong><span>perfiles conectados</span>
          <div className="radar-lines"><i /><i /><i /></div>
          <small className="hero-card-foot">{platformStats ? `${numberFormatter.format(platformStats.clubs)} clubes cubiertos` : "Calculando cobertura…"}</small>
        </div>
      </section>

      {error && <div className="notice" role="alert">{error}</div>}

      <section className="club-section" id="club" aria-busy={loading}>
        {loading ? (
          <div className="loading-panel" role="status"><span className="loader" /><p>Preparando la información del club…</p></div>
        ) : club ? (
          <ClubView key={club.id} club={club} squad={squad} />
        ) : null}
      </section>

      <footer>
        <a className="brand footer-brand" href="#inicio"><span className="brand-mark">PH</span><span>PlayerHub</span></a>
        <p>Información futbolística clara, propia y trazable.</p><span>Versión piloto · Argentina</span>
      </footer>
    </main>
  );
}
