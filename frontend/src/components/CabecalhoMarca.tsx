// Faixa verde-petróleo com o logo e o nome do app (como na tela de login do PDF).

interface Props {
  subtitulo?: string;
}

export default function CabecalhoMarca({
  subtitulo = "Custos, manutenções e projetos do seu carro num só lugar.",
}: Props) {
  return (
    <header className="capa">
      <img className="capa__icone" src="/icone.svg" alt="" width={56} height={56} />
      <h1 className="capa__titulo">Meu Veículo</h1>
      <p className="capa__subtitulo">{subtitulo}</p>
    </header>
  );
}
