interface Props {
  titulo: string;
  etapa: number;
  descricao: string;
}

// Abas da barra inferior cujos módulos ainda não foram construídos.
// A tela diz isso claramente, em vez de mostrar botões sem função.
export default function EmBrevePage({ titulo, etapa, descricao }: Props) {
  return (
    <main className="conteudo conteudo--topo">
      <h1 className="titulo-pagina">{titulo}</h1>
      <section className="cartao">
        <p className="cartao__titulo">Ainda não disponível</p>
        <p className="texto-suave">
          {descricao} Este módulo será entregue na etapa {etapa} do projeto.
        </p>
      </section>
    </main>
  );
}
