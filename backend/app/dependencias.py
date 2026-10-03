"""Montagem das camadas para cada requisição (injeção de dependências).

É aqui que cada peça recebe a de baixo:
    sessão do banco → repository → service → controller

As routes pedem o controller pronto com Depends(...). Nos testes, dá para
trocar só a engine (app.dependency_overrides[obter_engine]) e todo o resto
passa a usar o banco de teste.

Também ficam aqui as proteções usadas pelas routes:
- SessaoAtualDep: exige usuário logado (401 se não houver sessão válida);
- AdminDep: exige perfil admin (403 para os demais);
- verificar_cabecalho_do_app: recusa gravações que não vieram do app;
- exigir_banco_atualizado: 503 com explicação se o banco estiver numa versão
  diferente da que o código espera (em vez de erro 500 no meio do uso).
"""

import logging
from collections.abc import Iterator
from datetime import timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.banco.conexao import obter_engine
from app.banco.sessao import UnidadeDeTrabalho, abrir_sessao
from app.banco.versao import problema_de_versao
from app.config import Configuracoes, obter_configuracoes
from app.controllers.abastecimento_controller import AbastecimentoController
from app.controllers.medicao_tanque_controller import MedicaoTanqueController
from app.controllers.admin_controller import AdminController
from app.controllers.auth_controller import AuthController, ConfigCookie, ler_token
from app.controllers.diagnostico_controller import DiagnosticoController
from app.controllers.foto_controller import FotoController
from app.controllers.gasto_controller import GastoController
from app.controllers.historico_controller import HistoricoController
from app.controllers.manutencao_controller import ManutencaoController
from app.controllers.painel_controller import PainelController
from app.controllers.projeto_controller import ProjetoController
from app.controllers.saude_controller import SaudeController
from app.controllers.veiculo_controller import VeiculoController
from app.entities.sessao import SessaoAtual
from app.repositories.abastecimento_repository import AbastecimentoRepository
from app.repositories.medicao_tanque_repository import MedicaoTanqueRepository
from app.repositories.admin_repository import AdminRepository
from app.repositories.diagnostico_repository import DiagnosticoRepository
from app.repositories.foto_repository import FotoRepository
from app.repositories.gasto_repository import FinancasRepository, GastoRepository
from app.repositories.historico_repository import HistoricoRepository
from app.repositories.leitura_km_repository import LeituraKmRepository
from app.repositories.manutencao_repository import ManutencaoRepository, PlanoRepository
from app.repositories.projeto_repository import ProjetoRepository
from app.repositories.recuperacao_senha_repository import RecuperacaoSenhaRepository
from app.repositories.saude_repository import SaudeRepository
from app.repositories.sessao_repository import SessaoRepository
from app.repositories.tentativa_acesso_repository import TentativaAcessoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.repositories.veiculo_repository import VeiculoRepository
from app.services.abastecimento_service import AbastecimentoService
from app.services.medicao_tanque_service import MedicaoTanqueService
from app.services.admin_service import AdminService
from app.services.autenticacao_service import AutenticacaoService
from app.services.custo_service import CustoService
from app.services.diagnostico_service import DiagnosticoService
from app.services.email_service import EnviadorEmail, criar_enviador
from app.services.erros import AcessoNegado, ServicoIndisponivel
from app.services.foto_service import FotoService
from app.services.gasto_service import FinancasService, GastoService
from app.services.historico_service import HistoricoService
from app.services.manutencao_service import ManutencaoService, PlanoService
from app.services.painel_service import PainelService
from app.services.projeto_service import ProjetoService
from app.services.quilometragem_service import QuilometragemService
from app.services.saude_service import SaudeService
from app.services.senha_service import SenhaService
from app.services.veiculo_service import VeiculoService

CABECALHO_DO_APP = "X-MV-Requisicao"
METODOS_QUE_GRAVAM = {"POST", "PUT", "PATCH", "DELETE"}

ConfigDep = Annotated[Configuracoes, Depends(obter_configuracoes)]


def obter_sessao(engine: Annotated[Engine, Depends(obter_engine)]) -> Iterator[Session]:
    """Uma sessão por requisição. Ao fechar, o que não foi confirmado é desfeito."""
    with abrir_sessao(engine) as sessao:
        yield sessao


SessaoDep = Annotated[Session, Depends(obter_sessao)]


@lru_cache
def obter_senha_service() -> SenhaService:
    return SenhaService()


def obter_enviador_email(cfg: ConfigDep) -> EnviadorEmail:
    return criar_enviador(cfg)


def obter_autenticacao_service(
    sessao: SessaoDep,
    senhas: Annotated[SenhaService, Depends(obter_senha_service)],
    cfg: ConfigDep,
) -> AutenticacaoService:
    return AutenticacaoService(
        UnidadeDeTrabalho(sessao),
        UsuarioRepository(sessao),
        SessaoRepository(sessao),
        RecuperacaoSenhaRepository(sessao),
        TentativaAcessoRepository(sessao),
        senhas,
        validade_sessao=timedelta(days=cfg.sessao_dias),
        validade_link=timedelta(minutes=cfg.recuperacao_minutos),
        url_frontend=cfg.url_frontend,
        validade_convite=timedelta(days=cfg.convite_dias),
        validade_confirmacao=timedelta(hours=cfg.confirmacao_horas),
    )


AutenticacaoServiceDep = Annotated[AutenticacaoService, Depends(obter_autenticacao_service)]


def obter_auth_controller(
    service: AutenticacaoServiceDep,
    enviador: Annotated[EnviadorEmail, Depends(obter_enviador_email)],
    cfg: ConfigDep,
) -> AuthController:
    cookie = ConfigCookie(seguro=cfg.cookie_seguro, duracao_segundos=cfg.sessao_dias * 86400)
    return AuthController(service, enviador, cookie)


def obter_saude_controller(sessao: SessaoDep) -> SaudeController:
    return SaudeController(SaudeService(SaudeRepository(sessao)))


def obter_veiculo_controller(sessao: SessaoDep) -> VeiculoController:
    uow = UnidadeDeTrabalho(sessao)
    veiculos = VeiculoRepository(sessao)
    return VeiculoController(
        VeiculoService(uow, veiculos, FotoRepository(sessao)),
        QuilometragemService(uow, veiculos, LeituraKmRepository(sessao), MedicaoTanqueService(
            uow, veiculos, AbastecimentoRepository(sessao), LeituraKmRepository(sessao),
            MedicaoTanqueRepository(sessao))),
    )


def obter_foto_controller(sessao: SessaoDep) -> FotoController:
    return FotoController(FotoService(
        UnidadeDeTrabalho(sessao), VeiculoRepository(sessao), FotoRepository(sessao),
        ManutencaoRepository(sessao), DiagnosticoRepository(sessao), ProjetoRepository(sessao),
    ))


def obter_projeto_controller(sessao: SessaoDep) -> ProjetoController:
    return ProjetoController(ProjetoService(
        UnidadeDeTrabalho(sessao), VeiculoRepository(sessao), ProjetoRepository(sessao)))


def _manutencao_service(sessao: Session, uow: UnidadeDeTrabalho, veiculos: VeiculoRepository,
                        planos: PlanoRepository) -> ManutencaoService:
    return ManutencaoService(uow, veiculos, planos, ManutencaoRepository(sessao),
                             LeituraKmRepository(sessao), FotoRepository(sessao),
                             DiagnosticoRepository(sessao))


def obter_manutencao_controller(sessao: SessaoDep) -> ManutencaoController:
    uow = UnidadeDeTrabalho(sessao)
    veiculos = VeiculoRepository(sessao)
    planos = PlanoRepository(sessao)
    return ManutencaoController(
        PlanoService(uow, veiculos, planos),
        _manutencao_service(sessao, uow, veiculos, planos),
    )


def obter_diagnostico_controller(sessao: SessaoDep) -> DiagnosticoController:
    uow = UnidadeDeTrabalho(sessao)
    veiculos = VeiculoRepository(sessao)
    return DiagnosticoController(DiagnosticoService(
        uow, veiculos, DiagnosticoRepository(sessao), ManutencaoRepository(sessao),
        LeituraKmRepository(sessao), FotoRepository(sessao),
        _manutencao_service(sessao, uow, veiculos, PlanoRepository(sessao)),
    ))


def obter_abastecimento_controller(sessao: SessaoDep) -> AbastecimentoController:
    return AbastecimentoController(AbastecimentoService(
        UnidadeDeTrabalho(sessao), VeiculoRepository(sessao), AbastecimentoRepository(sessao),
        LeituraKmRepository(sessao), MedicaoTanqueRepository(sessao),
    ))


def obter_medicao_tanque_controller(sessao: SessaoDep) -> MedicaoTanqueController:
    return MedicaoTanqueController(MedicaoTanqueService(
        UnidadeDeTrabalho(sessao), VeiculoRepository(sessao), AbastecimentoRepository(sessao),
        LeituraKmRepository(sessao), MedicaoTanqueRepository(sessao),
    ))


def obter_gasto_controller(sessao: SessaoDep) -> GastoController:
    veiculos = VeiculoRepository(sessao)
    return GastoController(
        GastoService(UnidadeDeTrabalho(sessao), veiculos, GastoRepository(sessao)),
        FinancasService(veiculos, FinancasRepository(sessao)),
    )


def obter_painel_controller(sessao: SessaoDep) -> PainelController:
    veiculos = VeiculoRepository(sessao)
    financas = FinancasRepository(sessao)
    custo = CustoService(veiculos, financas, LeituraKmRepository(sessao))
    return PainelController(
        PainelService(veiculos, financas, GastoRepository(sessao), AbastecimentoRepository(sessao),
                      MedicaoTanqueRepository(sessao), custo),
        custo,
    )


def obter_historico_controller(sessao: SessaoDep) -> HistoricoController:
    return HistoricoController(HistoricoService(VeiculoRepository(sessao), HistoricoRepository(sessao)))


def obter_admin_controller(
    sessao: SessaoDep,
    autenticacao: AutenticacaoServiceDep,
    senhas: Annotated[SenhaService, Depends(obter_senha_service)],
    enviador: Annotated[EnviadorEmail, Depends(obter_enviador_email)],
) -> AdminController:
    return AdminController(AdminService(
        UnidadeDeTrabalho(sessao), AdminRepository(sessao), UsuarioRepository(sessao),
        SessaoRepository(sessao), RecuperacaoSenhaRepository(sessao), autenticacao, senhas,
    ), enviador)


# --------------------------------------------------------------------- proteções

def obter_sessao_atual(requisicao: Request, service: AutenticacaoServiceDep) -> SessaoAtual:
    return service.sessao_atual(ler_token(requisicao))


SessaoAtualDep = Annotated[SessaoAtual, Depends(obter_sessao_atual)]


def exigir_admin(atual: SessaoAtualDep) -> SessaoAtual:
    if not atual.usuario.eh_admin:
        raise AcessoNegado("Área restrita a administradores.")
    return atual


AdminDep = Annotated[SessaoAtual, Depends(exigir_admin)]


def avisar_se_banco_desatualizado() -> None:
    """Ao ligar o backend: avisa no terminal se o banco precisa de "gerenciar.py migrar"."""
    log = logging.getLogger("app")
    try:
        problema = problema_de_versao(obter_engine())
    except Exception:  # banco desligado, senha errada...: a tela "Situação do sistema" explica
        log.warning("Não foi possível conferir a versão do banco ao iniciar.")
        return
    if problema:
        log.warning("ATENÇÃO: %s", problema)


def exigir_banco_atualizado(engine: Annotated[Engine, Depends(obter_engine)]) -> None:
    """Todas as rotas, menos /api/saude (que mostra as pendências na tela
    "Situação do sistema"), exigem o banco na versão do código."""
    problema = problema_de_versao(engine)
    if problema:
        raise ServicoIndisponivel(problema)


def verificar_cabecalho_do_app(requisicao: Request) -> None:
    """Proteção contra requisições forjadas (CSRF).

    Um site malicioso consegue fazer o navegador enviar um formulário para a
    API com o cookie da sessão, mas não consegue acrescentar cabeçalhos
    próprios. Toda gravação exige o cabeçalho que só o app envia.
    """
    if requisicao.method in METODOS_QUE_GRAVAM and requisicao.headers.get(CABECALHO_DO_APP) != "1":
        raise AcessoNegado("Requisição recusada: ela não veio do aplicativo Meu Veículo.")
