# Interfaz web de PlayerHub

Aplicación web en español para explorar clubes, planteles y situaciones contractuales. En desarrollo consume la API configurada mediante `NEXT_PUBLIC_API_URL`; en producción usa la API pública de PlayerHub como respaldo seguro.

## Demo pública

- Aplicación: https://playerhub-thiagoramas.tramascai.chatgpt.site
- API: https://playerhub-oac3.onrender.com/docs

## Desarrollo

```powershell
npm install
npm run dev
```

La interfaz se abre en el puerto que informa el servidor de desarrollo y espera la API en `http://localhost:8000`.

## Docker

Desde la raíz del proyecto:

```powershell
docker compose up -d --build frontend
```

Luego abrir `http://localhost:3000`.
