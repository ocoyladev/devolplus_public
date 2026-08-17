import type { IDoesFilterPassParams } from "ag-grid-community";
import { type CustomFilterProps, useGridFilter } from "ag-grid-react";
import { useCallback } from "react";

import { OPCIONES_CARTA } from "./colores";

interface FiltroModel {
  // Texto de búsqueda "contiene" (el filtro que la columna ya tenía).
  texto?: string;
  // Estados seleccionados; "SIN" agrupa a los casos sin cartas.
  estados?: string[];
}

function componerModelo(texto: string, estados: string[]): FiltroModel | null {
  const t = texto.trim();
  const m: FiltroModel = {};
  if (t) m.texto = t;
  if (estados.length > 0) m.estados = estados;
  return t || estados.length > 0 ? m : null;
}

/**
 * Filtro de la columna CARTA: conserva el "contiene" de texto y AÑADE el filtro
 * por estado de vencimiento. Una fila pasa si cumple AMBAS condiciones activas.
 */
export function CartaFilter({
  model,
  onModelChange,
  getValue,
}: CustomFilterProps<Record<string, unknown>, unknown, FiltroModel>): JSX.Element {
  const texto = model?.texto ?? "";
  const estados = model?.estados ?? [];

  const doesFilterPass = useCallback(
    (params: IDoesFilterPassParams): boolean => {
      const t = model?.texto ?? "";
      const es = model?.estados ?? [];
      const valor = String(getValue(params.node) ?? "").toLowerCase();
      const textoOk = t === "" || valor.includes(t.toLowerCase());
      const estado =
        String(
          (params.node.data as Record<string, unknown> | undefined)?.carta_estado ?? "",
        ).trim() || "SIN";
      const estadoOk = es.length === 0 || es.includes(estado);
      return textoOk && estadoOk;
    },
    [model, getValue],
  );

  useGridFilter({ doesFilterPass });

  function alternar(clave: string): void {
    const set = new Set(estados);
    if (set.has(clave)) set.delete(clave);
    else set.add(clave);
    onModelChange(componerModelo(texto, [...set]));
  }

  return (
    <div className="min-w-[190px] p-2 text-sm">
      <input
        type="text"
        value={texto}
        onChange={(e) => onModelChange(componerModelo(e.target.value, estados))}
        placeholder="Contiene…"
        aria-label="Filtrar por texto"
        className="mb-2 w-full rounded border px-2 py-1 text-sm"
      />
      <p className="mb-1 font-medium text-slate-600">Filtrar por estado</p>
      {OPCIONES_CARTA.map((o) => (
        <label key={o.clave} className="flex cursor-pointer items-center gap-2 py-0.5">
          <input
            type="checkbox"
            aria-label={o.etiqueta}
            checked={estados.includes(o.clave)}
            onChange={() => alternar(o.clave)}
          />
          <span
            className="inline-block h-3.5 w-3.5 rounded border border-slate-300"
            style={{ backgroundColor: o.color ?? "transparent" }}
          />
          <span>{o.etiqueta}</span>
        </label>
      ))}
    </div>
  );
}
