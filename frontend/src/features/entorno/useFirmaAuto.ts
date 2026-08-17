import { useCallback, useEffect, useState } from "react";

import { fetchFirmaAutoEstado } from "../../api/entorno";

export interface EstadoFirmaAuto {
  disponible: boolean;
  motivo: string;
  perfil: string | null;
}

/**
 * Consulta UNA vez (al montar) si la firma automática puede activarse. Ya no se
 * re-consulta ante resize/focus (causaba recálculos constantes que impedían la
 * carga). Para re-detectar tras conectar/desconectar un monitor, usar
 * ``recargar`` (botón "Recalcular pantalla" en Mantenimiento).
 */
export function useFirmaAuto(): EstadoFirmaAuto & {
  recargar: () => Promise<EstadoFirmaAuto>;
} {
  const [estado, setEstado] = useState<EstadoFirmaAuto>({
    disponible: false,
    motivo: "",
    perfil: null,
  });

  const recargar = useCallback(async (): Promise<EstadoFirmaAuto> => {
    let nuevo: EstadoFirmaAuto;
    try {
      const e = await fetchFirmaAutoEstado();
      nuevo = {
        disponible: e.disponible,
        motivo: e.disponible ? "Activar firma automática por coordenadas" : e.motivo,
        perfil: e.perfil,
      };
    } catch {
      nuevo = { disponible: false, motivo: "No se pudo detectar la pantalla.", perfil: null };
    }
    setEstado(nuevo);
    return nuevo;
  }, []);

  useEffect(() => {
    void recargar();
  }, [recargar]);

  return { ...estado, recargar };
}
