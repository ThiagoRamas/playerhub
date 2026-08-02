import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

async function render(pathname = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request(`http://localhost${pathname}`, { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("No encontrado", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("renderiza la portada de PlayerHub en español", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /<html lang="es-AR">/i);
  assert.match(html, /PlayerHub/);
  assert.match(html, /El fútbol, jugador por jugador/);
  assert.match(html, /Buscá un club/);
  assert.doesNotMatch(html, /codex-preview/);
});

test("elimina la vista temporal de la plantilla", async () => {
  const [page, layout] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
  ]);
  assert.match(page, /Plantel y préstamos/);
  assert.match(layout, /lang="es-AR"/);
  await assert.rejects(access(new URL("../app/_sites-preview", root)));
});

test("renderiza la ruta individual de un jugador", async () => {
  const response = await render("/jugadores/15");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /Preparando la ficha del jugador/);

  const [home, playerPage] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/jugadores/[id]/page.tsx", import.meta.url), "utf8"),
  ]);
  assert.match(home, /href=\{`\/jugadores\/\$\{player\.id\}`\}/);
  assert.match(playerPage, /Historial del jugador/);
  assert.match(playerPage, /Valor de mercado/);
  assert.match(playerPage, /Transferencias/);
  assert.match(playerPage, /Lesiones/);
  assert.match(playerPage, /partido ausente/);
  assert.match(playerPage, /partidos ausentes/);
});
