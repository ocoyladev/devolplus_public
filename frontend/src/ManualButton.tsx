// Botón pequeño "?" de acceso al manual de usuario (se abre en pestaña nueva).
// Presente en todas las pantallas: acceso/solicitud, estado y vista principal.
export function ManualButton({ className = "" }: { className?: string }): JSX.Element {
  return (
    <a
      href="/manual/"
      target="_blank"
      rel="noreferrer noopener"
      title="Abrir el manual de usuario"
      aria-label="Manual de usuario"
      className={
        "inline-flex h-6 w-6 items-center justify-center rounded-full border " +
        "text-sm font-semibold text-slate-600 hover:bg-slate-100 " +
        className
      }
    >
      ?
    </a>
  );
}
