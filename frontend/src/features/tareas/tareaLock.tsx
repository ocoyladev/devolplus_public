import { createContext, useCallback, useContext } from "react";

/**
 * Lock global de "una tarea a la vez": mientras hay una tarea en segundo plano
 * (job) en ejecución, se deshabilitan el resto de acciones que lanzan tareas,
 * evitando envíos duplicados por doble-click o por lanzar dos masivas a la vez.
 *
 * - ``iniciar()`` es un guard SÍNCRONO (ref) que devuelve ``false`` si ya hay una
 *   tarea en curso: así un doble-click se ignora aunque React aún no haya
 *   repintado los botones deshabilitados.
 * - El lock se suelta con ``terminar()``: al fallar el arranque, al terminar una
 *   acción que no era un job, o cuando llega el ``job_done`` (lo llama App).
 *
 * NO bloquea la interacción con la tabla (filtros, orden, cambio de vista): esos
 * controles no consumen este lock.
 */
export interface TareaLock {
  /** Hay una tarea en segundo plano en ejecución (para deshabilitar botones). */
  ocupado: boolean;
  /** Toma el lock de forma síncrona. ``false`` si ya había una tarea en curso. */
  iniciar: () => boolean;
  /** Suelta el lock. */
  terminar: () => void;
}

export const TareaLockContext = createContext<TareaLock | null>(null);

/**
 * Lock nulo (sin bloqueo) que se usa cuando un componente se renderiza fuera de
 * un ``<TareaLockContext.Provider>`` (p. ej. en pruebas unitarias aisladas). La
 * app real siempre monta el provider en ``App``, así que aquí solo evita acoplar
 * cada componente al provider. Identidad estable a nivel de módulo para no
 * romper las dependencias de ``useCallback``.
 */
const LOCK_NULO: TareaLock = {
  ocupado: false,
  iniciar: () => true,
  terminar: () => {},
};

export function useTareaLock(): TareaLock {
  return useContext(TareaLockContext) ?? LOCK_NULO;
}

/**
 * Despachador estándar de una acción con el lock global tomado.
 *
 * - Si ya hay una tarea en curso, ignora la nueva (anti doble-click).
 * - Si la acción devuelve un ``job_id`` (string no vacío) es un job: mantiene el
 *   lock hasta que llegue ``job_done`` (App llama ``terminar``).
 * - Si la acción no es un job (``void``/datos), suelta el lock al resolverse.
 */
export function useLanzarTarea(): (
  kind: string,
  fn: () => Promise<unknown>,
  onJobIniciado: (kind: string) => void,
  onError: (mensaje: string) => void,
) => Promise<void> {
  const { iniciar, terminar } = useTareaLock();
  return useCallback(
    async (kind, fn, onJobIniciado, onError) => {
      if (!iniciar()) return; // ya hay una tarea en curso: se ignora
      try {
        const res = await fn();
        onJobIniciado(kind);
        // Un job devuelve su job_id (string). Si no lo es, la acción ya terminó.
        if (typeof res !== "string" || res.length === 0) terminar();
      } catch (e) {
        onError(String(e));
        terminar();
      }
    },
    [iniciar, terminar],
  );
}
