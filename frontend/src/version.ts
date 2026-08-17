import { useEffect, useState } from "react";

// La versión la sirve el backend (GET /api/version, desde el archivo VERSION
// embebido en el .exe). Se consulta en runtime para que el frontend compilado
// (dist) no dependa de con qué versión se empaquetó el ejecutable: así se puede
// armar el .exe en una PC con solo Python, sin recompilar el frontend.
export function useAppVersion(): string {
  const [version, setVersion] = useState("");
  useEffect(() => {
    fetch("/api/version")
      .then((r) => (r.ok ? r.json() : null))
      .then((d: { version?: string } | null) => {
        if (d?.version) setVersion(d.version);
      })
      .catch(() => {
        /* sin conexión: se omite el badge de versión */
      });
  }, []);
  return version;
}
