"""Montagem das camadas para cada requisição (injeção de dependências).

É aqui que cada peça recebe a de baixo:
    sessão do banco → repository → service → controller

As routes pedem o controller pronto com Depends(...). Nos testes, dá para
trocar só a engine (app.dependency_overrides[obter_engine]) e todo o resto
passa a usar o banco de teste.

Também ficam aqui as proteções usadas pelas routes:
- SessaoAtualDep: exige usuário logado (401 se não houver sessão válida);
- AdminDep: exige perfil admin (403 para os demais);
- verificar_cabecalho_do_app: recusa gravações que não vieram do app.
"""

from collections.abc import Iterator
from datetime import timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.banco.conexao import obter_engine
from app.banco.sessao import UnidadeDeTrabalho, abrir_sessao
from app.config import Configuracoes, obter_configuracoes
from app.controllers.auth_controller import AuthController, ConfigCookie, ler_token
from app.controllers.foto_controller import FotoController
from app.controllers.saude_controller import SaudeController
from app.controllers.veiculo_controller import VeiculoController
from app.entities.sessao import SessaoAtual
from app.repositories.arquivo_foto_repository import ArquivoFotoRepository
from app.repositories.foto_repository import FotoRepository
from app.repositories.leitura_km_repository import LeituraKmRepository
from app.repositories.recuperacao_senha_repository import RecuperacaoSenhaRepository
from app.repositories.saude_repository import SaudeRepository
from app.repositories.sessao_repository import SessaoRepository
from app.repositories.tentativa_acesso_repository import TentativaAcessoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.repositories.veiculo_repository import VeiculoRepository
from app.services.autenticacao_service import AutenticacaoService
from app.services.email_service import EnviadorEmail, criar_enviador
from app.services.erros import AcessoNegado
from app.services.foto_service import FotoService
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
        QuilometragemService(uow, veiculos, LeituraKmRepository(sessao)),
    )


def obter_arquivos_de_foto(cfg: ConfigDep) -> ArquivoFotoRepository:
    return ArquivoFotoRepository(cfg.pasta_fotos)


def obter_foto_controller(
    sessao: SessaoDep,
    arquivos: Annotated[ArquivoFotoRepository, Depends(obter_arquivos_de_foto)],
) -> FotoController:
    return FotoController(FotoService(
        UnidadeDeTrabalho(sessao), VeiculoRepository(sessao), FotoRepository(sessao), arquivos,
    ))


# --------------------------------------------------------------------- proteções

def obter_sessao_atual(requisicao: Request, service: AutenticacaoServiceDep) -> SessaoAtual:
    return service.sessao_atual(ler_token(requisicao))


SessaoAtualDep = Annotated[SessaoAtual, Depends(obter_sessao_atual)]


def exigir_admin(atual: SessaoAtualDep) -> SessaoAtual:
    if not atual.usuario.eh_admin:
        raise AcessoNegado("Área restrita a administradores.")
    return atual


AdminDep = Annotated[SessaoAtual, Depends(exigir_admin)]


def verificar_cabecalho_do_app(requisicao: Request) -> None:
    """Proteção contra requisições forjadas (CSRF).

    Um site malicioso consegue fazer o navegador enviar um formulário para a
    API com o cookie da sessão, mas não consegue acrescentar cabeçalhos
    próprios. Toda gravação exige o cabeçalho que só o app envia.
    """
    if requisicao.method in METODOS_QUE_GRAVAM and requisicao.headers.get(CABECALHO_DO_APP) != "1":
        raise AcessoNegado("Requisição recusada: ela não veio do aplicativo Meu Veículo.")
