import { useEffect, useState } from "react";

// Endereço temporário para mostrar, na própria tela, a imagem escolhida
// antes de enviar. Se o navegador não conseguir criar a pré-visualização,
// devolve null e o envio continua funcionando normalmente.
export function usePreviaDeArquivo(arquivo: File | null): string | null {
  const [previa, setPrevia] = useState<string | null>(null);

  useEffect(() => {
    if (!arquivo) {
      setPrevia(null);
      return;
    }
    let endereco: string | null = null;
    try {
      endereco = URL.createObjectURL(arquivo);
    } catch {
      endereco = null;
    }
    setPrevia(endereco);
    return () => {
      if (endereco) URL.revokeObjectURL(endereco); // libera a memória ao trocar ou sair
    };
  }, [arquivo]);

  return previa;
}
