import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { fetchArchivo, fetchTabla, type TablaResponse } from "./api/tabla";
import { descargas, procesos } from "./api/acciones";
import { getAcceso, type AccesoEstado } from "./api/acceso";
import { AutorLink } from "./autor";
import { ManualButton } from "./ManualButton";
import { useAppVersion } from "./version";
import { ConfigPanel } from "./features/config/ConfigPanel";
import { MantenimientoPanel } from "./features/mantenimiento/MantenimientoPanel";
import { AccesoScreen } from "./features/acceso/AccesoScreen";
import { CargarPanel } from "./features/datos/CargarPanel";
import { CasosTable } from "./features/table/CasosTable";
import type { ModoColumnas } from "./features/table/columnas";
import { MenuCaso } from "./features/procesos/MenuCaso";
import { Toolbar } from "./features/procesos/Toolbar";
import { ResultadoModal, type ResultadoPapelesTrabajo } from "./features/procesos/ResultadoModal";
import { EjecucionOverlay, type EjecucionRun } from "./features/procesos/EjecucionOverlay";
import { ResumenArchivarRepositorio } from "./features/archivo-repositorio/ResumenArchivarRepositorio";
import type { DetalleArchivar } from "./api/acciones";
import { SyncMenu } from "./features/sync/SyncMenu";
import { verificarServicios, type ServiciosEstado } from "./api/servicios";
import { useFirmaAuto } from "./features/entorno/useFirmaAuto";
import { useProgreso } from "./ws/useProgreso";
import { TareaLockContext, type TareaLock } from "./features/tareas/tareaLock";
import { Toast } from "./features/ui/Toast";

type Fila = Record<string, unknown>;

function dotColor(estado?: boolean | null): string {
  if (estado === undefined || estado === null) return "text-slate-300";
  return estado ? "text-green-600" : "text-red-500";
}

const KINDS_OVERLAY = new Set(["autorizar", "papeles_trabajo", "sistema_legacy_ref", "sistema_legacy_antec"]);

export default function App(): JSX.Element {
  const version = useAppVersion();
  const [tabla, setTabla] = useState<TablaResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filasSel, setFilasSel] = useState<Fila[]>([]);
  const [aviso, setAviso] = useState<string | null>(null);
  const [actividad, setActividad] = useState<string | null>(null);
  const [vista, setVista] = useState<"basicas" | "toda" | "archivo">("basicas");
  const modoColumnas: ModoColumnas = vista === "toda" ? "todas" : "default";
  const esArchivo = vista === "archivo";
  const [servicios, setServicios] = useState<ServiciosEstado | null>(null);
  const [verificando, setVerificando] = useState(false);
  const [acceso, setAcceso] = useState<AccesoEstado | null>(null);
  const [configInicial] = useState(false);
  const [resultadoPapelesTrabajo, setResultadoPapelesTrabajo] = useState<ResultadoPapelesTrabajo | null>(null);
  const [ejecucionRun, setEjecucionRun] = useState<EjecucionRun | null>(null);
  const [resumenArchivar, setResumenArchivar] = useState<DetalleArchivar[] | null>(null);
  const [progreso, setProgreso] = useState<{ done: number; total: number; etiqueta: string } | null>(null);
  const firmaAuto = useFirmaAuto();

  // Lock global "una tarea a la vez" (anti doble-click / masivas duplicadas).
  const [ocupado, setOcupado] = useState(false);
  const ocupadoRef = useRef(false);
  const iniciarTarea = useCallback((): boolean => {
    if (ocupadoRef.current) return false;
    ocupadoRef.current = true;
    setOcupado(true);
    return true;
  }, []);
  const terminarTarea = useCallback((): void => {
    ocupadoRef.current = false;
    setOcupado(false);
  }, []);
  const tareaLock = useMemo<TareaLock>(
    () => ({ ocupado, iniciar: iniciarTarea, terminar: terminarTarea }),
    [ocupado, iniciarTarea, terminarTarea],
  );

  const cargarAcceso = useCallback(() => {
    setAcceso(null);
    getAcceso()
      .then(setAcceso)
      .catch(() =>
        setAcceso({
          estado: "sin_conexion",
          usuario_red: "",
          mensaje: "No se pudo contactar con el servidor. Reintente.",
        }),
      );
  }, []);

  useEffect(() => cargarAcceso(), [cargarAcceso]);

  function verificar(): void {
    setVerificando(true);
    verificarServicios()
      .then(setServicios)
      .catch(() => setServicios({ portal: false, workflow: false }))
      .finally(() => setVerificando(false));
  }

  function reintentarDescargas(): void {
    if (!iniciarTarea()) return; // ya hay una tarea en curso
    descargas
      .reintentar()
      .then(() => setActividad("Reintentando descargas pendientes…"))
      .catch((e: unknown) => {
        mostrarAviso(String(e));
        terminarTarea();
      });
  }

  const recargar = useCallback(() => {
    const fn = vista === "archivo" ? fetchArchivo : fetchTabla;
    fn()
      .then(setTabla)
      .catch((e: unknown) => setError(String(e)));
  }, [vista]);

  useEffect(() => recargar(), [recargar]);

  const mostrarAviso = useCallback((m: string) => {
    setAviso(m);
    window.setTimeout(() => setAviso(null), 4000);
  }, []);

  const manejarJobIniciado = useCallback((kind: string) => {
    if (KINDS_OVERLAY.has(kind)) {
      setEjecucionRun({ kind, log: [], done: 0, total: 0, etiqueta: "" });
    } else {
      setActividad(`Iniciando ${kind}…`);
    }
  }, []);

  useProgreso((e) => {
    if (e.type === "progress") {
      // 'validar_archivo' no es un job: nunca llega su job_done, así que la
      // barra global se quedaría colgada. Su avance lo pinta el propio modal.
      if (e.kind === "validar_archivo") return;
      if (e.kind && KINDS_OVERLAY.has(e.kind)) {
        setEjecucionRun((prev) =>
          prev && prev.kind === e.kind
            ? {
                ...prev,
                log: e.msg ? [...prev.log, e.msg] : prev.log,
                done: typeof e.done === "number" ? e.done : prev.done,
                total: typeof e.total === "number" ? e.total : prev.total,
                etiqueta: e.etiqueta ?? prev.etiqueta,
              }
            : prev,
        );
      }
      if (typeof e.total === "number" && e.total > 0) {
        setProgreso({ done: e.done ?? 0, total: e.total, etiqueta: e.etiqueta ?? "" });
      } else {
        setActividad(e.msg ?? null);
      }
    } else if (e.type === "job_done") {
      setActividad(null);
      setProgreso(null);
      terminarTarea(); // suelta el lock global al terminar la tarea
      const kind = String(e.kind ?? "");
      if (KINDS_OVERLAY.has(kind)) {
        setEjecucionRun(null);
        const esRef = kind === "sistema_legacy_ref";
        const esAntec = kind === "sistema_legacy_antec";
        setResultadoPapelesTrabajo({
          ok: Boolean(e.ok),
          mensaje: e.ok ? e.mensaje ?? "Proceso completado." : e.error ?? "El proceso falló.",
          okCount: e.ok_count,
          oks: e.oks ?? [],
          errores: e.errores ?? [],
          tituloExito: esRef
            ? "REF/Tiempos (SISTEMA_LEGACY) — completado"
            : esAntec
              ? "Antecedentes (SISTEMA_LEGACY) — completado"
              : kind === "autorizar"
                ? "Autorizar — completado"
                : "Generar PAPELES_TRABAJO — completado",
          tituloError: esRef
            ? "REF/Tiempos (SISTEMA_LEGACY) — finalizó con errores"
            : esAntec
              ? "Antecedentes (SISTEMA_LEGACY) — finalizó con errores"
              : kind === "autorizar"
                ? "Autorizar — finalizó con errores"
                : "Generar PAPELES_TRABAJO — finalizó con errores",
        });
        // Autorizar y PAPELES_TRABAJO modifican la tabla; SISTEMA_LEGACY no.
        if (kind === "autorizar" || kind === "papeles_trabajo") recargar();
        return;
      }
      // Descarga masiva de cartas: modal con oks / ya descargadas / omitidas.
      if (kind === "descarga_cartas_masivo") {
        setResultadoPapelesTrabajo({
          ok: Boolean(e.ok),
          mensaje: e.ok ? e.mensaje ?? "Descarga completada." : e.error ?? "La descarga falló.",
          okCount: e.ok_count,
          oks: e.oks ?? [],
          yaDescargadas: e.ya_descargadas ?? [],
          omitidos: e.omitidos ?? [],
          errores: e.errores ?? [],
          tituloExito: "Descargar cartas — completado",
          tituloError: "Descargar cartas — finalizó con errores",
        });
        return;
      }
      // Archivar REPOSITORIO: modal de resumen (desde la barra o la cola de mantenimiento).
      if (String(e.kind ?? "") === "archivar_repositorio") {
        setResumenArchivar(e.detalle ?? []);
        recargar();
        return;
      }
      if (e.ok) {
        mostrarAviso(e.mensaje ? `✓ ${e.mensaje}` : "✓ Proceso finalizado");
        // Descargas y tickets Mesa de Ayuda no modifican la tabla: no recargar.
        const k = String(e.kind ?? "");
        if (!k.startsWith("mesa_ayuda") && !k.startsWith("descarga")) recargar();
        // Casos preexistentes en archivo: ofrecer desarchivarlos.
        if (e.archivados && e.archivados.length > 0) {
          const ok = window.confirm(
            "Los siguientes casos ya estaban en archivo y NO se cargaron:\n" +
              e.archivados.join(", ") +
              "\n\n¿Desea desarchivarlos?",
          );
          if (ok) {
            procesos
              .recuperar(e.archivados)
              .then(() => setActividad("Desarchivando casos…"))
              .catch((err: unknown) => mostrarAviso(String(err)));
          }
        }
      } else {
        mostrarAviso(`✗ ${e.error ?? "Error en el proceso"}`);
      }
    }
  });

  const numDocs = filasSel.map((r) => String(r.num_doc ?? "")).filter(Boolean);

  // Compuerta de acceso: solo con verificación "permitido" se abre la app.
  if (acceso === null) {
    return (
      <div className="flex h-screen items-center justify-center text-slate-400">
        Verificando acceso…
      </div>
    );
  }
  if (acceso.estado !== "permitido") {
    return <AccesoScreen acceso={acceso} onReintentar={cargarAcceso} />;
  }

  return (
    <TareaLockContext.Provider value={tareaLock}>
    <div className="flex h-screen flex-col bg-slate-50">
      <header className="flex items-center gap-4 border-b bg-white px-4 py-2 shadow-sm">
        <h1 className="text-lg font-semibold text-slate-800">DEVOL+</h1>
        <span className="text-sm text-slate-500">
          {tabla ? `${tabla.total} casos` : error ? "error" : "cargando…"}
        </span>
        {progreso ? (
          <span className="flex items-center gap-2 text-sm text-blue-600">
            <progress className="h-2 w-40" value={progreso.done} max={progreso.total} />
            <span>
              {progreso.etiqueta ? `${progreso.etiqueta} — ` : ""}
              {progreso.done}/{progreso.total}
            </span>
          </span>
        ) : actividad ? (
          <span className="text-sm text-blue-600">⏳ {actividad}</span>
        ) : null}
        <div className="ml-auto flex items-center gap-3">
          <select
            value={vista}
            onChange={(e) => setVista(e.target.value as "basicas" | "toda" | "archivo")}
            className="rounded border px-2 py-1 text-sm"
            title="Vista de la tabla"
          >
            <option value="basicas">Columnas básicas</option>
            <option value="toda">Toda la data</option>
            <option value="archivo">Tabla de archivo</option>
          </select>
          <button
            onClick={recargar}
            title="Actualizar la tabla de la interfaz"
            aria-label="Actualizar tabla"
            className="rounded border px-2 py-1 text-sm hover:bg-slate-100"
          >
            ↻
          </button>
          <SyncMenu
            onJobIniciado={(kind) => setActividad(`Iniciando ${kind}…`)}
            onError={mostrarAviso}
          />
          <ConfigPanel onAviso={mostrarAviso} abrirInicial={configInicial} />
          <MantenimientoPanel
            onAviso={mostrarAviso}
            onJobIniciado={(kind) => setActividad(`Iniciando ${kind}…`)}
            onRecalcularPantalla={firmaAuto.recargar}
          />
          <CargarPanel
            onJobIniciado={(kind) => setActividad(`Iniciando ${kind}…`)}
            onError={mostrarAviso}
          />
          <div className="flex items-center gap-2 border-l pl-3 text-xs text-slate-600">
            <span title="Estado de login en Portal / E-Doc">
              Portal/E-Doc{" "}
              <span className={dotColor(servicios?.portal)}>●</span>
            </span>
            <span title="Estado de login en Workflow">
              Workflow <span className={dotColor(servicios?.workflow)}>●</span>
            </span>
            <button
              onClick={verificar}
              disabled={verificando}
              title="Inicia sesión en Portal y Workflow con las credenciales guardadas y muestra si el login fue exitoso"
              className="rounded border px-2 py-0.5 hover:bg-slate-100 disabled:opacity-50"
            >
              {verificando ? "Verificando…" : "Verificar login"}
            </button>
            <button
              onClick={reintentarDescargas}
              disabled={ocupado}
              title="Reprocesar las descargas pendientes en la cola"
              className="rounded border px-2 py-0.5 hover:bg-slate-100 disabled:opacity-50"
            >
              ↻ Descargas
            </button>
          </div>
          <ManualButton />
        </div>
      </header>

      {tabla && tabla.total > 0 ? (
        <Toolbar
          seleccion={numDocs}
          filas={filasSel}
          firmaAutoDisponible={firmaAuto.disponible}
          firmaAutoMotivo={firmaAuto.motivo}
          archivo={esArchivo}
          onJobIniciado={manejarJobIniciado}
          onError={mostrarAviso}
          menuCaso={
            filasSel.length === 1 ? (
              <MenuCaso
                row={filasSel[0]}
                tablaArchivo={esArchivo}
                onJobIniciado={(kind) => setActividad(`Iniciando ${kind}…`)}
                onError={mostrarAviso}
                onDatosCambiados={recargar}
              />
            ) : null
          }
        />
      ) : null}

      <main className="flex-1 p-2">
        {error ? (
          <p className="p-4 text-red-600">No se pudo cargar la tabla: {error}</p>
        ) : tabla && tabla.total === 0 ? (
          <p className="p-4 text-slate-500">
            {esArchivo
              ? "No hay casos archivados."
              : "No hay casos cargados. Cárgalos desde la aplicación y vuelve a abrir."}
          </p>
        ) : tabla ? (
          <CasosTable
            columns={tabla.columns}
            rows={tabla.rows}
            modo={modoColumnas}
            editable={!esArchivo}
            tablaArchivo={esArchivo}
            onSelectionChanged={setFilasSel}
            onJobIniciado={(kind) => setActividad(`Iniciando ${kind}…`)}
            onError={mostrarAviso}
            onDatosCambiados={recargar}
          />
        ) : (
          <p className="p-4 text-slate-500">Cargando…</p>
        )}
      </main>

      <EjecucionOverlay run={ejecucionRun} />

      <ResultadoModal
        resultado={resultadoPapelesTrabajo}
        onClose={() => setResultadoPapelesTrabajo(null)}
      />

      <ResumenArchivarRepositorio
        detalle={resumenArchivar}
        onClose={() => setResumenArchivar(null)}
      />

      <footer className="border-t bg-white px-4 py-1 text-center text-xs text-slate-400">
        Diseñado por <AutorLink>Oscar Arnold Coyla Urquizo</AutorLink>
        {version ? (
          <span className="ml-2 font-mono text-slate-300">v{version}</span>
        ) : null}
      </footer>
      <Toast mensaje={aviso} />
    </div>
    </TareaLockContext.Provider>
  );
}
