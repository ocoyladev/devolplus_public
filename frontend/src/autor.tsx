// Enlace del autor (LinkedIn) y utilidades para enlazar su nombre en textos.
export const AUTOR_URL = "https://www.linkedin.com/in/ocoyladev";

// Coincide con "Oscar Arnold Coyla Urquizo" o el más corto "Oscar Coyla".
const RE_AUTOR = /Oscar(?: Arnold)? Coyla(?: Urquizo)?/g;

export function AutorLink({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <a
      href={AUTOR_URL}
      target="_blank"
      rel="noreferrer noopener"
      className="font-medium text-blue-600 hover:underline"
      title="Ver perfil de LinkedIn de Oscar Coyla"
    >
      {children}
    </a>
  );
}

/** Renderiza un texto enlazando cada mención del nombre del autor a LinkedIn. */
export function TextoAutor({ texto }: { texto: string }): JSX.Element {
  const partes: React.ReactNode[] = [];
  let ultimo = 0;
  for (const m of texto.matchAll(RE_AUTOR)) {
    const inicio = m.index ?? 0;
    if (inicio > ultimo) partes.push(texto.slice(ultimo, inicio));
    partes.push(<AutorLink key={inicio}>{m[0]}</AutorLink>);
    ultimo = inicio + m[0].length;
  }
  if (ultimo < texto.length) partes.push(texto.slice(ultimo));
  return <>{partes}</>;
}
