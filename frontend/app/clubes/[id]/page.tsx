"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import ClubView, { type ClubDetail, type SquadMember } from "../../components/club-view";
import { API_URL } from "../../lib/config";

export default function ClubPage() {
  const params = useParams();
  const rawId = params.id;
  const clubId = Number(Array.isArray(rawId) ? rawId[0] : rawId);
  const [club, setClub] = useState<ClubDetail | null>(null);
  const [squad, setSquad] = useState<SquadMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isInteger(clubId) || clubId <= 0) {
      setError("El club solicitado no es válido.");
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    async function loadClub() {
      try {
        const [detailResponse, squadResponse] = await Promise.all([
          fetch(`${API_URL}/api/v1/clubs/${clubId}`, { signal: controller.signal }),
          fetch(`${API_URL}/api/v1/clubs/${clubId}/squad`, { signal: controller.signal }),
        ]);
        if (!detailResponse.ok || !squadResponse.ok) throw new Error();
        const [detail, members] = await Promise.all([detailResponse.json(), squadResponse.json()]);
        setClub(detail as ClubDetail);
        setSquad(members as SquadMember[]);
      } catch (reason) {
        if (!(reason instanceof DOMException && reason.name === "AbortError")) setError("No pudimos cargar la información del club.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void loadClub();
    return () => controller.abort();
  }, [clubId]);

  return (
    <main className="club-page">
      <header className="site-header">
        <a className="brand" href="/" aria-label="PlayerHub, inicio"><span className="brand-mark">PH</span><span>PlayerHub</span></a>
        <nav aria-label="Navegación principal"><a href="/clubes">Todos los clubes</a><a href="/jugadores">Jugadores</a><span className="language-badge">ES</span></nav>
      </header>

      <section className="club-section club-page-section" aria-busy={loading}>
        <a className="club-back-link" href="/clubes">← Volver a todos los clubes</a>
        {loading ? (
          <div className="loading-panel" role="status"><span className="loader" /><p>Preparando la ficha del club…</p></div>
        ) : error || !club ? (
          <div className="player-loading" role="alert"><span className="empty-mark">!</span><h1>No encontramos el club</h1><p>{error}</p><a className="primary-link" href="/">Volver al inicio</a></div>
        ) : (
          <ClubView club={club} squad={squad} />
        )}
      </section>

      <footer><a className="brand footer-brand" href="/"><span className="brand-mark">PH</span><span>PlayerHub</span></a><p>Información futbolística clara, propia y trazable.</p><span>Versión piloto · Argentina</span></footer>
    </main>
  );
}
