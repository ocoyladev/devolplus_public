import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";

import type {
  CellClickedEvent,
  CellKeyDownEvent,
  CellValueChangedEvent,
  ColDef,
  SelectionChangedEvent,
} from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import type { CSSProperties } from "react";
import { useMemo, useRef, useState } from "react";

import { abrir, descargas } from "../../api/acciones";
import { actualizarCampo } from "../../api/campos";
import { useTareaLock } from "../tareas/tareaLock";
import { CartasPanel } from "../cartas/CartasPanel";
import { campoDeField, construirColumnas, type ModoColumnas } from "./columnas";
import { textoCeldaCartaConReserva } from "./colores";
import { AG_GRID_LOCALE_ES } from "./locale";

interface Props {
  columns: string[];
  rows: Record<string, unknown>[];
  modo?: ModoColumnas;
  editable?: boolean;
  tablaArchivo?: boolean;
  onSelectionChanged?: (rows: Record<string, unknown>[]) => void;
  onJobIniciado?: (kind: string) => void;
  onError?: (mensaje: string) => void;
  /** Se invoca tras un cambio persistido en el panel de cartas, para recargar la tabla. */
  onDatosCambiados?: () => void;
}

export function CasosTable({
  columns,
  rows,
  modo = "default",
  editable = true,
  tablaArchivo = false,
  onSelectionChanged,
  onJobIniciado,
  onError,
  onDatosCambiados,
}: Props): JSX.Element {
  // Campo cuyo valor se está confirmando con Enter (para disparar descarga).
  const enterField = useRef<string | null>(null);
  // La edición de celdas sigue libre; solo la descarga auto (CARTA/RI con Enter)
  // respeta el lock global "una tarea a la vez".
  const { iniciar, terminar } = useTareaLock();
  // num_doc cuyo panel de cartas está abierto, o null.
  const [cartasDe, setCartasDe] = useState<string | null>(null);
  // True si el panel se abrió con "+" (caso sin cartas): abre directo en el
  // formulario de alta (spec §9).
  const [altaInmediata, setAltaInmediata] = useState(false);

  const colDefs = useMemo<ColDef[]>(() => {
    // Columna de selección con checkbox + "seleccionar todo" sobre filas filtradas.
    const selCol: ColDef = {
      headerName: "",
      checkboxSelection: true,
      headerCheckboxSelection: true,
      headerCheckboxSelectionFilteredOnly: true,
      width: 48,
      minWidth: 48,
      pinned: "left",
      filter: false,
      sortable: false,
      resizable: false,
      suppressMovable: true,
    };
    const cols = construirColumnas(columns, modo, editable);
    for (const c of cols) {
      if (c.field !== "carta") continue;
      c.cellRenderer = (p: { data: Record<string, unknown> }) => {
        const sinCartas = Number(p.data?.carta_n ?? 0) === 0;
        return (
          <span className="flex items-center justify-between gap-1">
            <span>
              {textoCeldaCartaConReserva(
                p.data?.carta_vigente,
                p.data?.carta_n,
                p.data?.carta,
              )}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setAltaInmediata(sinCartas);
                setCartasDe(String(p.data?.num_doc ?? ""));
              }}
              title="Ver / editar cartas"
              className="rounded px-1 text-xs text-slate-500 hover:bg-slate-200"
            >
              {sinCartas ? "+" : "⌄"}
            </button>
          </span>
        );
      };
    }
    return [selCol, ...cols];
  }, [columns, modo, editable]);

  const defaultColDef = useMemo<ColDef>(
    () => ({ minWidth: 40, filterParams: { buttons: ["reset"] } }),
    [],
  );

  function handleSelection(e: SelectionChangedEvent): void {
    if (!onSelectionChanged) return;
    onSelectionChanged(e.api.getSelectedRows() as Record<string, unknown>[]);
  }

  function handleCellKeyDown(e: CellKeyDownEvent): void {
    const ev = e.event as KeyboardEvent | undefined;
    if (!ev || ev.key !== "Enter") return;
    const f = e.colDef?.field;
    if (f === "num_ri" || f === "ri") {
      enterField.current = f;
      return;
    }
    if (f !== "carta") return;
    // La columna CARTA ya no es editable: el Enter dispara la descarga aquí.
    const row = e.data as Record<string, unknown>;
    if (!iniciar()) return;
    descargas
      .cartas(row, tablaArchivo)
      .then(() => onJobIniciado?.("descarga_cartas"))
      .catch((err: unknown) => {
        onError?.(String(err));
        terminar();
      });
  }

  function handleCellClick(e: CellClickedEvent): void {
    // Triple clic → abrir la carpeta del caso (evita el conflicto del doble clic
    // con la selección de texto de la celda).
    const ev = e.event as MouseEvent | undefined;
    if (ev && ev.detail === 3) {
      abrir
        .carpeta(e.data as Record<string, unknown>, tablaArchivo)
        .catch((err: unknown) => onError?.(String(err)));
    }
  }

  async function handleCellValueChanged(e: CellValueChangedEvent): Promise<void> {
    const field = e.colDef.field;
    if (!field) return;
    const campo = campoDeField(field);
    if (!campo) return;
    const numDoc = String((e.data as Record<string, unknown>).num_doc ?? "");
    if (!numDoc) return;

    const valor = e.newValue == null ? "" : String(e.newValue);
    try {
      await actualizarCampo(numDoc, campo, valor);
    } catch (err) {
      e.node.setDataValue(field, e.oldValue);
      onError?.(String(err));
      enterField.current = null;
      return;
    }

    // Si el cambio se confirmó con Enter en RI: tras guardar, descargar.
    const conEnter = enterField.current;
    enterField.current = null;
    if (conEnter === field) {
      const row = e.data as Record<string, unknown>;
      // El valor ya se guardó. La descarga auto se omite si hay otra tarea en
      // curso (evita jobs concurrentes); puede relanzarse re-confirmando la celda.
      if (iniciar()) {
        descargas
          .ri(row)
          .then(() => onJobIniciado?.("descarga_ri"))
          .catch((err: unknown) => {
            onError?.(String(err));
            terminar();
          });
      }
    }
  }

  return (
    <div
      className="ag-theme-quartz h-full w-full"
      style={{ "--ag-font-size": "13px" } as CSSProperties}
    >
      <AgGridReact
        rowData={rows}
        columnDefs={colDefs}
        defaultColDef={defaultColDef}
        localeText={AG_GRID_LOCALE_ES}
        rowSelection="multiple"
        rowMultiSelectWithClick={true}
        onSelectionChanged={handleSelection}
        onCellKeyDown={handleCellKeyDown}
        onCellValueChanged={(e) => void handleCellValueChanged(e)}
        onCellClicked={handleCellClick}
        onCellEditingStarted={() => {
          enterField.current = null;
        }}
        enableCellTextSelection={true}
        ensureDomOrder={true}
        animateRows={true}
        stopEditingWhenCellsLoseFocus={true}
      />
      {cartasDe !== null ? (
        <CartasPanel
          numDoc={cartasDe}
          altaInmediata={altaInmediata}
          onClose={() => setCartasDe(null)}
          onCambio={onDatosCambiados}
        />
      ) : null}
    </div>
  );
}
