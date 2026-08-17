interface Props {
  mensaje: string | null;
}

/**
 * Toast/Snackbar fijo en la parte inferior. Al ser `fixed` (overlay), no altera
 * la composición ni la posición del resto de elementos (a diferencia de la
 * antigua barra amarilla, que empujaba el contenido). Se muestra sobre modales.
 */
export function Toast({ mensaje }: Props): JSX.Element | null {
  if (!mensaje) return null;
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-4 z-[100] flex justify-center px-4">
      <div className="pointer-events-auto max-w-[90vw] rounded-lg bg-slate-800/95 px-4 py-2 text-sm text-white shadow-lg ring-1 ring-black/10">
        {mensaje}
      </div>
    </div>
  );
}
