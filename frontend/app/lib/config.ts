const PRODUCTION_API_URL = "https://playerhub-oac3.onrender.com";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? PRODUCTION_API_URL;
