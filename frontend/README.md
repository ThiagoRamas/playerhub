# Interfaz web de PlayerHub

Aplicación web en español para explorar clubes, planteles y situaciones contractuales. Consume la API local de PlayerHub mediante `NEXT_PUBLIC_API_URL`.

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
