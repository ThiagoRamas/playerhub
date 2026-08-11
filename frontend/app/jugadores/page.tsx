"use client";

import { FormEvent, useState } from "react";
import { API_URL } from "../lib/config";
import { translateCountry } from "../lib/translations";

type PlayerSummary = {
  id: number;
  display_name: string;
  image_url: string | null;
  date_of_birth: string | null;
  position: string | null;
  citizenships: string[];
  current_clubs: string[];
  latest_market_value: number | null;
};

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

const moneyFormatter = new Intl.NumberFormat("es-AR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

function translatePosition(position: string | null) {
  return position ? positionLabels[position] ?? position : "Posición sin informar";
}

function formatMarketValue(value: number | null) {
  return value === null ? "Sin cotización" : moneyFormatter.format(value);
}

function initials(name: string) {
  return name.split(" ").map((part) => part[0]).slice(0, 2).join("");
}

export default function PlayersPage() {
  const [query, setQuery] = useState("");
  const [players, setPlayers] = useState<PlayerSummary[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const term = query.trim();
    if (term.length < 2) return;

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_URL}/api/v1/players?search=${encodeURIComponent(term)}&limit=50`,
      );
      if (!response.ok) throw new Error();
      setPlayers((await response.json()) as PlayerSummary[]);
      setSearched(true);
    } catch {
      setError("No pudimos buscar jugadores. Intentá nuevamente.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="players-catalog-page">
      <header className="site-header">
        <a className="brand" href="/" aria-label="PlayerHub, inicio"><span className="brand-mark">PH</span><span>PlayerHub</span></a>
        <nav aria-label="Navegación principal"><a href="/clubes">Clubes</a><a href="/jugadores" aria-current="page">Jugadores</a><span className="language-badge">ES</span></nav>
      </header>

      <section className="players-search-hero">
        <span className="eyebrow">Más de mil perfiles</span>
        <h1>Encontrá a cualquier jugador.</h1>
        <p>Buscá por nombre o apellido y accedé a su trayectoria, rendimiento, transferencias, lesiones y valor de mercado.</p>
        <form className="players-search-form" onSubmit={handleSubmit} role="search">
          <label className="sr-only" htmlFor="player-search">Buscar un jugador</label>
          <input id="player-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ejemplo: Lautaro Martínez" minLength={2} />
          <button type="submit" disabled={loading || query.trim().length < 2}>{loading ? "Buscando…" : "Buscar jugador"}</button>
        </form>
      </section>

      <section className="players-results" aria-busy={loading}>
        <div className="players-results-heading"><div><span className="section-label">Futbolistas</span><h2>Resultados de búsqueda</h2></div>{searched && <span>{players.length} {players.length === 1 ? "jugador" : "jugadores"}</span>}</div>
        {error ? (
          <div className="notice" role="alert">{error}</div>
        ) : loading ? (
          <div className="loading-panel" role="status"><span className="loader" /><p>Buscando perfiles…</p></div>
        ) : !searched ? (
          <div className="players-search-empty"><span>PH</span><h3>Empezá por un nombre</h3><p>Podés buscar jugadores de cualquiera de los 81 clubes argentinos cargados.</p></div>
        ) : players.length ? (
          <div className="players-catalog-grid">
            {players.map((player) => (
              <a className="player-search-card" href={`/jugadores/${player.id}`} key={player.id}>
                <div className="player-search-photo">{player.image_url ? <img src={player.image_url} alt={`Foto de ${player.display_name}`} loading="lazy" /> : <span>{initials(player.display_name)}</span>}</div>
                <div className="player-search-copy"><span>{translatePosition(player.position)}</span><h3>{player.display_name}</h3><p>{player.current_clubs.join(" · ") || "Club sin informar"}</p><small>{player.citizenships.map(translateCountry).join(" · ") || "Nacionalidad sin informar"}</small></div>
                <div className="player-search-value"><span>Valor actual</span><strong>{formatMarketValue(player.latest_market_value)}</strong><i aria-hidden="true">→</i></div>
              </a>
            ))}
          </div>
        ) : (
          <div className="players-search-empty"><span>?</span><h3>No encontramos coincidencias</h3><p>Probá con otro nombre o revisá cómo está escrito.</p></div>
        )}
      </section>

      <footer><a className="brand footer-brand" href="/"><span className="brand-mark">PH</span><span>PlayerHub</span></a><p>Información futbolística clara, propia y trazable.</p><span>Versión piloto · Argentina</span></footer>
    </main>
  );
}
