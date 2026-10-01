"""Formatos JSON de veículos, leituras de quilometragem e fotos.

- Entradas usam extra="forbid": campos como "usuario_id", "ativo" ou
  "quilometragem" (na edição) são recusados, não ignorados.
- Dinheiro entra e sai como TEXTO ("65000.00"), nunca como número com
  ponto flutuante, para não perder centavos.
- Datas são "AAAA-MM-DD" (dia do calendário, sem hora e sem fuso).
- Os limites de tamanho aqui só evitam textos gigantes; as regras ficam
  nos services, com mensagens em português.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _recusar_float(valor):
    if isinstance(valor, float):
        raise ValueError("Envie o valor como texto, por exemplo \"65000.00\".")
    return valor


Dinheiro = Annotated[Decimal, BeforeValidator(_recusar_float)]


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VeiculoEdicaoEntrada(_Entrada):
    marca: str = Field(max_length=300)
    modelo: str = Field(max_length=300)
    versao: str | None = Field(default=None, max_length=300)
    ano: int
    placa: str = Field(max_length=30)
    cor: str | None = Field(default=None, max_length=300)
    tipo_combustivel: str = Field(max_length=30)
    data_aquisicao: date | None = None
    valor_aquisicao: Dinheiro | None = None
    km_aquisicao: int | None = None


class VeiculoEntrada(VeiculoEdicaoEntrada):
    # A quilometragem só é informada no cadastro; depois, muda por leituras.
    quilometragem: int


class VeiculoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    marca: str
    modelo: str
    versao: str | None
    ano: int
    placa: str
    cor: str | None
    tipo_combustivel: str
    quilometragem: int
    # Dia da leitura que define a quilometragem atual; null = data desconhecida.
    data_leitura_km: date | None
    km_aquisicao: int | None
    data_aquisicao: date | None
    valor_aquisicao: Decimal | None
    ativo: bool
    criado_em: datetime
    em_uso: bool
    foto_capa_id: int | None


# ------------------------------------------------------------- quilometragem

class LeituraEntrada(_Entrada):
    quilometragem: int
    data_leitura: date | None = None  # vazio = hoje


class CorrecaoLeituraEntrada(_Entrada):
    quilometragem: int
    motivo: str | None = Field(default=None, max_length=1000)


class AnulacaoLeituraEntrada(_Entrada):
    motivo: str | None = Field(default=None, max_length=1000)


class LeituraResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    veiculo_id: int
    quilometragem: int
    data_leitura: date | None
    origem: str
    origem_id: int | None
    corrige_id: int | None
    valida: bool
    editavel: bool
    anulada_em: datetime | None
    motivo_anulacao: str | None
    criado_em: datetime


class PaginaLeituras(BaseModel):
    itens: list[LeituraResposta]
    total: int
    pagina: int
    por_pagina: int


# --------------------------------------------------------------------- fotos

class FotoEdicaoEntrada(_Entrada):
    legenda: str | None = Field(default=None, max_length=1000)
    data_foto: date | None = None
    # UM registro do mesmo veículo ao qual a foto fica ligada (todos vazios = sem
    # vínculo); momento (antes/depois) só com projeto.
    manutencao_id: int | None = None
    diagnostico_id: int | None = None
    projeto_id: int | None = None
    momento: str | None = Field(default=None, max_length=10)


class FotoResposta(BaseModel):
    """Metadados da foto. O caminho do arquivo no servidor não é exposto:
    a imagem é obtida em /api/veiculos/{veiculo_id}/fotos/{id}/arquivo."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    veiculo_id: int
    tipo_mime: str
    tamanho_bytes: int
    legenda: str | None
    data_foto: date
    principal: bool
    projeto_id: int | None
    momento: str | None
    diagnostico_id: int | None
    manutencao_id: int | None
    criado_em: datetime


class PaginaFotos(BaseModel):
    itens: list[FotoResposta]
    total: int
    pagina: int
    por_pagina: int
