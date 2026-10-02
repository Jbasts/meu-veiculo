"""Formatos JSON da área de administração. Nenhuma resposta tem senha, hash ou token."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AlterarUsuarioEntrada(_Entrada):
    perfil: str = Field(max_length=10)   # padrao | admin
    ativo: bool


class ConviteEntrada(_Entrada):
    nome: str = Field(max_length=300)
    email: str = Field(max_length=320)


class UsuarioAdminResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    perfil: str
    ativo: bool
    ultimo_acesso: datetime | None    # null = nunca entrou (ex.: convite ainda não aceito)
    criado_em: datetime
    veiculos_ativos: int
    veiculos: int


class VeiculoComDonoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    marca: str
    modelo: str
    ano: int
    placa: str
    ativo: bool
    dono_nome: str
    dono_ativo: bool


class PorPerfilResposta(BaseModel):
    admin: int
    padrao: int


class PaginaUsuariosAdmin(BaseModel):
    itens: list[UsuarioAdminResposta]
    total: int
    pagina: int
    por_pagina: int
    por_perfil: PorPerfilResposta


class PaginaVeiculosAdmin(BaseModel):
    itens: list[VeiculoComDonoResposta]
    total: int
    pagina: int
    por_pagina: int


class UsuarioDetalheAdminResposta(BaseModel):
    usuario: UsuarioAdminResposta
    veiculos: list[VeiculoComDonoResposta]


class ResumoAdminResposta(BaseModel):
    usuarios: int
    veiculos: int


class LinkEnviadoResposta(BaseModel):
    tipo: str            # convite | recuperacao
    mensagem: str


class ConviteResposta(BaseModel):
    detalhe: UsuarioDetalheAdminResposta
    mensagem: str
