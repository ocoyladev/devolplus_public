import { useEffect, useRef, useState } from "react";

import type { DetalleArchivar } from "../api/acciones";

export interface ProgresoEvento {
  type: "progress" | "job_done";
  job_id: string;
  kind?: string;
  num_doc?: string | null;
  msg?: string;
  ok?: boolean;
  error?: string;
  mensaje?: string | null;
  archivados?: string[];
  errores?: { caso: string; motivo: string }[];
  ok_count?: number;
  oks?: string[];
  ya_descargadas?: string[];
  omitidos?: string[];
  detalle?: DetalleArchivar[];
  done?: number;
  total?: number;
  etiqueta?: string;
}

/**
 * Conecta al WebSocket /ws y entrega los eventos de progreso/fin de job al
 * callback (vía ref, para no reconectar en cada render).
 *
 * `activo` permite a un consumidor efímero (un modal) conectarse solo mientras
 * está abierto, en vez de mantener una conexión extra durante toda la sesión.
 */
export function useProgreso(
  onEvento?: (e: ProgresoEvento) => void,
  activo = true,
): {
  conectado: boolean;
} {
  const cbRef = useRef(onEvento);
  cbRef.current = onEvento;
  const [conectado, setConectado] = useState(false);

  useEffect(() => {
    if (!activo) {
      setConectado(false);
      return;
    }
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/ws`);
    ws.onopen = () => setConectado(true);
    ws.onclose = () => setConectado(false);
    ws.onmessage = (ev: MessageEvent<string>) => {
      try {
        const data = JSON.parse(ev.data) as ProgresoEvento;
        if (data.type === "progress" || data.type === "job_done") {
          cbRef.current?.(data);
        }
      } catch {
        // mensaje no-JSON: se ignora
      }
    };
    return () => ws.close();
  }, [activo]);

  return { conectado };
}
