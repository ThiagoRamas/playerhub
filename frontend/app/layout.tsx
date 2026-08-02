import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: "PlayerHub | Datos de fútbol, jugador por jugador",
  description: "Explorá planteles, préstamos, trayectorias y valores de mercado en PlayerHub.",
  openGraph: {
    title: "PlayerHub",
    description: "El fútbol, jugador por jugador.",
    locale: "es_AR",
    type: "website",
    images: [{ url: "/og.png", width: 1734, height: 907, alt: "PlayerHub, datos de fútbol" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "PlayerHub",
    description: "El fútbol, jugador por jugador.",
    images: ["/og.png"],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="es-AR"><body>{children}</body></html>;
}
