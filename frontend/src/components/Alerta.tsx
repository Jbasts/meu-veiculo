import type { ReactNode } from "react";

interface Props {
  tipo: "erro" | "sucesso" | "info";
  children: ReactNode;
}

export default function Alerta({ tipo, children }: Props) {
  return (
    <div className={`alerta alerta--${tipo}`} role={tipo === "erro" ? "alert" : "status"}>
      {children}
    </div>
  );
}
