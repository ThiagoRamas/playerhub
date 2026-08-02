"use client";

import { useMemo, useState } from "react";

export type ClubSummary = {
  id: number;
  name: string;
  slug: string | null;
  country: string | null;
  logo_url: string | null;
  is_complete: boolean;
};

export type ClubDetail = ClubSummary & {
  team_type: string;
  data_as_of: string | null;
  linked_players: number;
};

type SquadStatus = "SQUAD" | "ON_LOAN" | "LOANED_OUT";

export type SquadMember = {
  id: number;
  display_name: string;
  image_url: string | null;
  date_of_birth: string | null;
  position: string | null;
  citizenships: string[];
  latest_market_value: number | null;
  membership_type: string;
  squad_status: SquadStatus;
};

type Filter = "ACTIVE" | "SQUAD" | "ON_LOAN" | "LOANED_OUT" | "ALL";

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

const statusLabels: Record<SquadStatus, string> = {
  SQUAD: "En el plantel",
  ON_LOAN: "A préstamo",
  LOANED_OUT: "Cedido a otro club",
};

const filters: Array<{ value: Filter; label: string }> = [
  { value: "ACTIVE", label: "Plantel actual" },
  { value: "SQUAD", label: "Propios" },
  { value: "ON_LOAN", label: "A préstamo" },
  { value: "LOANED_OUT", label: "Cedidos" },
  { value: "ALL", label: "Todos" },
];

const moneyFormatter = new Intl.NumberFormat("es-AR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

const dateFormatter = new Intl.DateTimeFormat("es-AR", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

export function translateCountry(country: string) {
  return countryLabels[country] ?? country;
}

function translatePosition(position: string | null) {
  if (!position) return "Posición sin informar";
  return positionLabels[position] ?? position;
}

function calculateAge(dateOfBirth: string | null) {
  if (!dateOfBirth) return null;
  const birth = new Date(`${dateOfBirth}T00:00:00`);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const beforeBirthday =
    today.getMonth() < birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate());
  if (beforeBirthday) age -= 1;
  return age;
}

function formatMarketValue(value: number | null) {
  return value === null ? "Sin cotización" : moneyFormatter.format(value);
}

export default function ClubView({ club, squad }: { club: ClubDetail; squad: SquadMember[] }) {
  const [filter, setFilter] = useState<Filter>("ACTIVE");

  const filteredSquad = useMemo(() => {
    if (filter === "ALL") return squad;
    if (filter === "ACTIVE") return squad.filter((member) => member.squad_status !== "LOANED_OUT");
    return squad.filter((member) => member.squad_status === filter);
  }, [filter, squad]);

  const stats = useMemo(() => {
    const active = squad.filter((member) => member.squad_status !== "LOANED_OUT");
    return {
      active: active.length,
      onLoan: squad.filter((member) => member.squad_status === "ON_LOAN").length,
      loanedOut: squad.filter((member) => member.squad_status === "LOANED_OUT").length,
      marketValue: active.reduce((total, member) => total + (member.latest_market_value ?? 0), 0),
    };
  }, [squad]);

  return (
    <>
      <div className="club-heading">
        <div className="club-identity">
          <div className="club-logo">{club.logo_url ? <img src={club.logo_url} alt={`Escudo de ${club.name}`} /> : <span>PH</span>}</div>
          <div><span className="section-label">Ficha del club</span><h2><a href={`/clubes/${club.id}`}>{club.name}</a></h2><p>{translateCountry(club.country ?? "País sin informar")} · Primera división</p></div>
        </div>
        <div className="data-date"><span>Datos actualizados</span><strong>{club.data_as_of ? dateFormatter.format(new Date(`${club.data_as_of}T00:00:00`)) : "Sin fecha"}</strong></div>
      </div>

      <div className="stats-grid">
        <article><span>Plantel actual</span><strong>{stats.active}</strong><small>jugadores disponibles</small></article>
        <article><span>A préstamo</span><strong>{stats.onLoan}</strong><small>incorporados al club</small></article>
        <article><span>Cedidos</span><strong>{stats.loanedOut}</strong><small>en otras instituciones</small></article>
        <article className="value-stat"><span>Valor del plantel</span><strong>{moneyFormatter.format(stats.marketValue)}</strong><small>últimas cotizaciones</small></article>
      </div>

      <div className="squad-section" id="plantel">
        <div className="section-heading">
          <div><span className="section-label">Jugadores</span><h2>Plantel y préstamos</h2></div>
          <span className="result-count">{filteredSquad.length} jugadores</span>
        </div>
        <div className="filters" role="group" aria-label="Filtrar jugadores por situación">
          {filters.map((item) => (
            <button type="button" key={item.value} className={filter === item.value ? "active" : ""} onClick={() => setFilter(item.value)} aria-pressed={filter === item.value}>{item.label}</button>
          ))}
        </div>
        <div className="player-grid">
          {filteredSquad.map((player) => {
            const age = calculateAge(player.date_of_birth);
            return (
              <a className="player-card" key={player.id} href={`/jugadores/${player.id}`} aria-label={`Ver ficha de ${player.display_name}`}>
                <div className="player-photo">
                  {player.image_url ? <img src={player.image_url} alt={`Foto de ${player.display_name}`} loading="lazy" /> : <span>{player.display_name.split(" ").map((part) => part[0]).slice(0, 2).join("")}</span>}
                  <span className={`status status-${player.squad_status.toLowerCase()}`}>{statusLabels[player.squad_status]}</span>
                </div>
                <div className="player-info">
                  <span className="position">{translatePosition(player.position)}</span><h3>{player.display_name}</h3>
                  <p>{player.citizenships.map(translateCountry).join(" · ") || "Nacionalidad sin informar"}{age !== null ? ` · ${age} años` : ""}</p>
                  <div className="market-value"><span>Valor de mercado</span><strong>{formatMarketValue(player.latest_market_value)}</strong></div>
                </div>
              </a>
            );
          })}
        </div>
      </div>
    </>
  );
}
