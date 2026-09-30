import { Link } from "react-router";

export default function NaoEncontradaPage() {
  return (
    <div className="pagina">
      <main className="conteudo conteudo--topo">
        <h1 className="titulo-pagina">Página não encontrada</h1>
        <p className="subtitulo">O endereço aberto não existe no Meu Veículo.</p>
        <Link to="/" className="botao botao--primario">
          Ir para o início
        </Link>
      </main>
    </div>
  );
}
