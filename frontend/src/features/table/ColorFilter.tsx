import type { IDoesFilterPassParams } from "ag-grid-community";
import { type CustomFilterProps, useGridFilter } from "ag-grid-react";
import { useCallback } from "react";

import { colorClaveDe, opcionesColorDe } from "./colores";

interface FiltroModel {
  // Texto de búsqueda "contiene" (sin distinción de mayúsculas/acentos-no).
  texto?: string;
  // Claves de color seleccionadas (verde/naranja/gris/rojo/sin).
  claves?: string[];
}

function normalizar(v: unknown): string {
  return String(v ?? "").trim().toLowerCase();
}

/** Construye el modelo a partir de sus partes, o null si no hay filtro activo. */
function componerModelo(texto: string, claves: string[]): FiltroModel | null {
  const t = texto.trim();
  const m: FiltroModel = {};
  if (t) m.texto = t;
  if (claves.length > 0) m.claves = claves;
  return t || claves.length > 0 ? m : null;
}

/**
 * Filtro combinado para las columnas con color (RESULTADO y VCTO. IND.): mantiene
 * el filtro de texto ("contiene") y añade el filtro por color de la celda. Una
 * fila pasa si cumple AMBas condiciones activas.
 */
export function ColorFilter({
  model,
  onModelChange,
  colDef,
  getValue,
}: CustomFilterProps<Record<string, unknown>, unknown, FiltroModel>): JSX.Element {
  const field = colDef.field ?? "";
  const opciones = opcionesColorDe(field);
  const texto = model?.texto ?? "";
  const claves = model?.claves ?? [];

  const doesFilterPass = useCallback(
    (params: IDoesFilterPassParams): boolean => {
      const t = model?.texto ?? "";
      const cs = model?.claves ?? [];
      const valor = getValue(params.node);
      const textoOk = t === "" || normalizar(valor).includes(t.toLowerCase());
      const colorOk = cs.length === 0 || cs.includes(colorClaveDe(field, valor));
      return textoOk && colorOk;
    },
    [model, field, getValue],
  );

  useGridFilter({ doesFilterPass });

  function cambiarTexto(v: string): void {
    onModelChange(componerModelo(v, claves));
  }

  function alternar(clave: string): void {
    const set = new Set(claves);
    if (set.has(clave)) set.delete(clave);
    else set.add(clave);
    onModelChange(componerModelo(texto, [...set]));
  }

  return (
    <div className="min-w-[190px] p-2 text-sm">
      <input
        type="text"
        value={texto}
        onChange={(e) => cambiarTexto(e.target.value)}
        placeholder="Contiene…"
        aria-label="Filtrar por texto"
        className="mb-2 w-full rounded border px-2 py-1 text-sm"
      />
      <p className="mb-1 font-medium text-slate-600">Filtrar por color</p>
      {opciones.map((o) => (
        <label key={o.clave} className="flex cursor-pointer items-center gap-2 py-0.5">
          <input
            type="checkbox"
            checked={claves.includes(o.clave)}
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
