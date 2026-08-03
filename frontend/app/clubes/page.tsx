"use client";

import { useEffect, useMemo, useState } from "react";
import type { ClubSummary } from "../components/club-view";
import { translateCountry } from "../lib/translations";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function normalized(value: string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es");
}

export default function ClubsPage() {
  const [clubs, setClubs] = useState<ClubSummary[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function loadClubs() {
      try {
        const response = await fetch(
          `${API_URL}/api/v1/clubs?country=Argentina&limit=100`,
          { signal: controller.signal },
        );
        if (!response.ok) throw new Error();
        setClubs((await response.json()) as ClubSummary[]);
      } catch (reason) {
        if (!(reason instanceof DOMException && reason.name === "AbortError")) {
          setError("No pudimos cargar el catálogo de clubes.");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void loadClubs();
    return () => controller.abort();
  }, []);

  const filteredClubs = useMemo(() => {
    const term = normalized(query.trim());
    return term ? clubs.filter((club) => normalized(club.name).includes(term)) : clubs;
  }, [clubs, query]);

  return (
    <main className="catalog-page">
      <header className="site-header">
        <a className="brand" href="/" aria-label="PlayerHub, inicio"><span className="brand-mark">PH</span><span>PlayerHub</span></a>
        <nav aria-label="Navegación principal"><a href="/clubes" aria-current="page">Clubes</a><a href="/#club">Destacado</a><span className="language-badge">ES</span></nav>
      </header>

      <section className="catalog-hero">
        <span className="eyebrow">Argentina</span>
        <h1>Todos los clubes,<br />en un solo lugar.</h1>
        <p>Recorré los equipos disponibles y entrá a sus planteles, préstamos y perfiles de jugadores.</p>
        <div className="catalog-search">
          <label className="sr-only" htmlFor="catalog-filter">Filtrar clubes por nombre</label>
          <input id="catalog-filter" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filtrá por nombre del club" />
          <strong aria-live="polite">{filteredClubs.length}</strong>
        </div>
      </section>

      <section className="catalog-content" aria-busy={loading}>
        <div className="catalog-heading"><div><span className="section-label">Directorio</span><h2>Clubes disponibles</h2></div><span>{filteredClubs.length} {filteredClubs.length === 1 ? "resultado" : "resultados"}</span></div>
        {loading ? (
          <div className="loading-panel" role="status"><span className="loader" /><p>Cargando clubes…</p></div>
        ) : error ? (
          <div className="notice" role="alert">{error}</div>
        ) : filteredClubs.length ? (
          <div className="club-catalog-grid">
            {filteredClubs.map((club) => (
              <a className="catalog-card" href={`/clubes/${club.id}`} key={club.id}>
                <div className="catalog-logo">{club.logo_url ? <img src={club.logo_url} alt={`Escudo de ${club.name}`} loading="lazy" /> : <span>PH</span>}</div>
                <div><h3>{club.name}</h3><p>{translateCountry(club.country ?? "País sin informar")}</p></div>
                <span className="catalog-arrow" aria-hidden="true">→</span>
              </a>
            ))}
          </div>
        ) : (
          <p className="catalog-empty">No encontramos clubes con ese nombre.</p>
        )}
      </section>

      <footer><a className="brand footer-brand" href="/"><span className="brand-mark">PH</span><span>PlayerHub</span></a><p>Información futbolística clara, propia y trazable.</p><span>Versión piloto · Argentina</span></footer>
    </main>
  );
}
