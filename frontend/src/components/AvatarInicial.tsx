// Círculo com as iniciais do nome (como "P" e "RS" no PDF).
export function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "?";
  const primeira = partes[0][0];
  const ultima = partes.length > 1 ? partes[partes.length - 1][0] : "";
  return (primeira + ultima).toUpperCase();
}

export default function AvatarInicial({ nome }: { nome: string }) {
  return (
    <span className="avatar" aria-hidden="true">
      {iniciais(nome)}
    </span>
  );
}
