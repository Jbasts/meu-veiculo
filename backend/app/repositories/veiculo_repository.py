"""Acesso à tabela veiculo (e ao veículo em uso, guardado em usuario)."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.entities.usuario import Usuario
from app.entities.veiculo import Veiculo
from app.repositories.erros import PlacaJaCadastrada, restricao_violada

RESTRICAO_PLACA_UNICA = "veiculo_usuario_id_placa_key"


class VeiculoRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def buscar(self, veiculo_id: int) -> Veiculo | None:
        return self._sessao.get(Veiculo, veiculo_id)

    def bloquear(self, veiculo_id: int) -> Veiculo | None:
        """Busca o veículo e segura a linha até o fim da transação (SELECT ... FOR UPDATE).

        Duas alterações simultâneas do mesmo veículo (troca de capa, nova
        leitura de km) passam a acontecer uma depois da outra.
        """
        return self._sessao.scalar(
            select(Veiculo).where(Veiculo.id == veiculo_id).with_for_update()
            .execution_options(populate_existing=True)
        )

    def listar_do_usuario(self, usuario_id: int) -> list[Veiculo]:
        """Ativos primeiro; dentro de cada grupo, o mais recente primeiro."""
        return list(self._sessao.scalars(
            select(Veiculo).where(Veiculo.usuario_id == usuario_id)
            .order_by(Veiculo.ativo.desc(), Veiculo.id.desc())
        ))

    def _gravar(self) -> None:
        try:
            # SAVEPOINT: se a placa já existir, só esta gravação é desfeita.
            with self._sessao.begin_nested():
                self._sessao.flush()
        except IntegrityError as erro:
            if restricao_violada(erro) == RESTRICAO_PLACA_UNICA:
                raise PlacaJaCadastrada() from None
            raise

    def criar(self, usuario_id: int, dados: dict) -> Veiculo:
        veiculo = Veiculo(usuario_id=usuario_id, ativo=True, **dados)
        self._sessao.add(veiculo)
        try:
            self._gravar()
        except PlacaJaCadastrada:
            if veiculo in self._sessao:
                self._sessao.expunge(veiculo)
            raise
        # O trigger do banco cria a primeira leitura e preenche data_leitura_km.
        self._sessao.refresh(veiculo)
        return veiculo

    def atualizar(self, veiculo: Veiculo, dados: dict) -> None:
        for campo, valor in dados.items():
            setattr(veiculo, campo, valor)
        self._gravar()

    def definir_ativo(self, veiculo: Veiculo, ativo: bool) -> None:
        veiculo.ativo = ativo
        self._sessao.flush()

    def recarregar(self, veiculo: Veiculo) -> None:
        """Relê o veículo (o banco recalcula a quilometragem quando uma leitura muda)."""
        self._sessao.refresh(veiculo)

    def definir_em_uso(self, usuario: Usuario, veiculo_id: int | None) -> None:
        usuario.veiculo_em_uso_id = veiculo_id
        self._sessao.flush()
