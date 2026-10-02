"""Dados de exemplo para apresentar o Meu Veículo (TCC).

Uso: "gerenciar.py carregar-exemplo", que só grava no banco de DEMONSTRAÇÃO
(DB_NOME_DEMO, padrão meu_veiculo_demo). Nada disto roda nas migrations nem
no banco de desenvolvimento: o sistema continua funcionando com banco vazio.

Como os dados entram
    Pela própria API (como se alguém usasse as telas), com o cliente de teste
    do FastAPI. Assim valem exatamente as mesmas regras e conferências:
    quilometragem, totais em Decimal, tanque, vínculos do mesmo veículo,
    fotos regravadas etc. Por usar o cliente de teste, este comando precisa
    das dependências de desenvolvimento (requirements-dev.txt).

Datas
    Tudo é calculado a partir de HOJE (fuso America/Sao_Paulo): cerca de oito
    meses de histórico, terminando nesta semana. Assim o Início mostra gastos
    do mês, contas vencidas e manutenções próximas em qualquer dia em que a
    carga for feita.

Contas criadas (senha de exemplo abaixo; não é segredo, é só para a demonstração)
    paula@exemplo.com.br   administradora, com dois veículos e todo o histórico
    rafael@exemplo.com.br  perfil padrão, com um veículo (aparece na Administração)
"""

import io
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import Engine

from app.banco.sessao import UnidadeDeTrabalho, abrir_sessao
from app.dependencias import obter_engine
from app.main import app
from app.repositories.usuario_repository import UsuarioRepository
from app.services import calendario
from app.services.usuario_service import UsuarioService

SENHA_EXEMPLO = "meu veiculo de exemplo"
EMAIL_ADMIN = "paula@exemplo.com.br"
EMAIL_PADRAO = "rafael@exemplo.com.br"

KM_POR_DIA = 32          # o Civic de exemplo roda cerca de 1.000 km por mês
KM_HOJE = 85_000
DIAS_DE_HISTORICO = 240


class FalhaNaCarga(Exception):
    """A API recusou um dado de exemplo (mostra o endereço e a mensagem)."""


@dataclass
class Resumo:
    contas: list[str] = field(default_factory=list)
    veiculos: int = 0
    registros: int = 0
    fotos: int = 0


def _dinheiro(valor: Decimal) -> str:
    return str(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _fonte(tamanho: int):
    """Fonte do Windows com acentos; sem ela, a do Pillow (os acentos são retirados)."""
    for nome in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(nome, tamanho), True
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=tamanho), False
    except TypeError:  # Pillow sem FreeType
        return ImageFont.load_default(), False


def _imagem(titulo: str, cor: tuple[int, int, int]) -> bytes:
    """Uma "foto" desenhada (carro estilizado + título), para não depender de arquivos.

    Quadrada e com letras grandes, porque a galeria mostra miniaturas pequenas."""
    lado = 1000
    figura = Image.new("RGB", (lado, lado), cor)
    desenho = ImageDraw.Draw(figura)
    for faixa in range(0, lado, 25):  # leve degradê
        tom = tuple(max(0, c - faixa // 20) for c in cor)
        desenho.rectangle([0, faixa, lado, faixa + 25], fill=tom)
    branco, petroleo, dourado = (255, 255, 255), (11, 52, 64), (228, 163, 59)
    # Carro estilizado: carroceria, cabine e rodas.
    desenho.rounded_rectangle([170, 330, 830, 470], radius=50, fill=branco)
    desenho.polygon([(300, 330), (380, 220), (640, 220), (730, 330)], fill=branco)
    desenho.polygon([(330, 320), (395, 240), (500, 240), (500, 320)], fill=cor)
    desenho.polygon([(520, 320), (520, 240), (625, 240), (700, 320)], fill=cor)
    for centro in (330, 670):
        desenho.ellipse([centro - 70, 410, centro + 70, 550], fill=petroleo)
        desenho.ellipse([centro - 30, 450, centro + 30, 510], fill=dourado)
    # Título em até duas linhas, centralizado.
    fonte, com_acentos = _fonte(84)
    pequena, _ = _fonte(48)
    if not com_acentos:
        titulo = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    palavras, linhas = titulo.split(), [""]
    for palavra in palavras:
        tentativa = f"{linhas[-1]} {palavra}".strip()
        if desenho.textlength(tentativa, font=fonte) <= lado - 120 or not linhas[-1]:
            linhas[-1] = tentativa
        else:
            linhas.append(palavra)
    y = 640
    for linha in linhas[:2]:
        desenho.text((lado / 2, y), linha, fill=branco, font=fonte, anchor="mm")
        y += 100
    desenho.text((lado / 2, 900), "foto de exemplo", fill=dourado, font=pequena, anchor="mm")
    saida = io.BytesIO()
    figura.save(saida, "JPEG", quality=85)
    return saida.getvalue()


class _Carga:
    def __init__(self, hoje: date):
        self.hoje = hoje
        self.resumo = Resumo()

    # --------------------------------------------------------------- apoio
    def dia(self, dias_atras: int) -> str:
        return (self.hoje - timedelta(days=dias_atras)).isoformat()

    def km(self, dias_atras: int) -> int:
        return KM_HOJE - KM_POR_DIA * dias_atras

    def enviar(self, cliente: TestClient, metodo: str, caminho: str, dados=None, **extra) -> dict:
        resposta = cliente.request(metodo, f"/api{caminho}", json=dados, **extra)
        if resposta.status_code >= 400:
            raise FalhaNaCarga(f"{metodo} {caminho} → {resposta.status_code}: {resposta.text}")
        self.resumo.registros += 1
        return resposta.json() if resposta.content else {}

    def foto(self, cliente: TestClient, veiculo_id: int, titulo: str, cor, dias_atras: int,
             **campos) -> dict:
        dados = {"legenda": titulo, "data_foto": self.dia(dias_atras), **campos}
        resposta = cliente.post(
            f"/api/veiculos/{veiculo_id}/fotos",
            files={"arquivo": ("exemplo.jpg", _imagem(titulo, cor), "image/jpeg")},
            data={chave: str(valor).lower() if isinstance(valor, bool) else str(valor)
                  for chave, valor in dados.items()},
        )
        if resposta.status_code >= 400:
            raise FalhaNaCarga(f"foto '{titulo}' → {resposta.status_code}: {resposta.text}")
        self.resumo.fotos += 1
        return resposta.json()

    @staticmethod
    def conta(nome: str, email: str) -> TestClient:
        cliente = TestClient(app, headers={"X-MV-Requisicao": "1"})
        resposta = cliente.post("/api/auth/cadastro", json={
            "nome": nome, "email": email, "senha": SENHA_EXEMPLO,
            "confirmacao_senha": SENHA_EXEMPLO})
        if resposta.status_code != 201:
            raise FalhaNaCarga(f"cadastro de {email} → {resposta.status_code}: {resposta.text}")
        return cliente

    # ------------------------------------------------------------ o Civic
    def civic(self, paula: TestClient) -> None:
        civic = self.enviar(paula, "POST", "/veiculos", {
            "marca": "Honda", "modelo": "Civic", "versao": "EXL 2.0", "ano": 2020,
            "placa": "BRA2E19", "cor": "Prata", "tipo_combustivel": "flex",
            "quilometragem": KM_HOJE, "data_aquisicao": "2022-03-15",
            "valor_aquisicao": "65000.00", "km_aquisicao": 22000, "capacidade_tanque": "56.0"})
        v = civic["id"]
        self.resumo.veiculos += 1
        self.foto(paula, v, "Civic EXL prata", (27, 85, 102), 200, principal=True)

        self._abastecimentos_civic(paula, v)
        self._manutencoes_civic(paula, v)
        self._gastos_civic(paula, v)
        self._projetos_civic(paula, v)

    def _abastecimentos_civic(self, paula: TestClient, v: int) -> None:
        # (dias atrás, combustível, preço, tanque cheio, nível antes em oitavos, posto)
        # Gasolina no começo, uma fase de etanol e a volta para a gasolina: os
        # trechos de troca de combustível aparecem como "mistura" no consumo.
        roteiro = [
            (225, "gasolina", "5.890", True, None, "Posto Shell Av. Brasil"),
            (210, "gasolina", "5.890", True, None, "Posto Shell Av. Brasil"),
            (196, "gasolina", "5.990", True, None, "Posto Ipiranga Centro"),
            (182, "gasolina", "5.990", False, None, "Posto Ipiranga Centro"),
            (168, "gasolina", "6.090", True, None, "Posto Shell Av. Brasil"),
            (154, "etanol", "3.990", True, None, "Posto BR Rodovia"),
            (142, "etanol", "4.090", True, None, "Posto BR Rodovia"),
            (130, "etanol", "4.090", True, None, "Posto BR Rodovia"),
            (118, "etanol", "4.190", True, 2, "Posto Ipiranga Centro"),
            (106, "gasolina", "6.190", True, None, "Posto Shell Av. Brasil"),
            (92, "gasolina", "6.190", True, None, "Posto Shell Av. Brasil"),
            (78, "gasolina", "6.250", True, None, "Posto Ipiranga Centro"),
            (64, "gasolina", "6.250", True, 3, "Posto Shell Av. Brasil"),
            (50, "gasolina", "6.290", True, None, "Posto Shell Av. Brasil"),
            (36, "etanol", "4.290", True, None, "Posto BR Rodovia"),
            (24, "etanol", "4.290", True, None, "Posto BR Rodovia"),
            (12, "etanol", "4.290", True, None, "Posto BR Rodovia"),
            (3, "etanol", "4.390", True, None, "Posto BR Rodovia"),
        ]
        consumo = {"gasolina": Decimal("12.1"), "etanol": Decimal("8.6")}
        capacidade = Decimal("56.0")
        anterior = None
        falta = Decimal(0)  # litros que faltam para encher o tanque
        for dias, combustivel, preco, cheio, nivel, posto in roteiro:
            if anterior is None:
                litros = Decimal("40")
            else:
                falta += Decimal(self.km(dias) - self.km(anterior)) / consumo[combustivel]
                litros = falta if cheio else falta * Decimal("0.6")
                falta -= litros
            anterior = dias
            dados = {"combustivel": combustivel, "tipo": "comum", "data": self.dia(dias),
                     "quilometragem": self.km(dias),
                     "litros": str(litros.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)),
                     "valor_litro": preco, "tanque_cheio": cheio, "posto": posto}
            if nivel is not None:
                dados["nivel_antes"] = nivel
            self.enviar(paula, "POST", f"/veiculos/{v}/abastecimentos", dados)

        # Marcação do km e do nível no dia 1 do mês, como a Paula planejou.
        primeiro = self.hoje.replace(day=1)
        dias_desde_o_dia_1 = (self.hoje - primeiro).days
        dias_dos_abastecimentos = {d: c for d, c, *_ in roteiro}
        if dias_desde_o_dia_1 not in dias_dos_abastecimentos:  # não cair no dia de um abastecimento
            # Nível coerente com o que o carro gastou desde o último abastecimento (tanque cheio).
            ultimo = min(d for d in dias_dos_abastecimentos if d > dias_desde_o_dia_1)
            combustivel_no_tanque = dias_dos_abastecimentos[ultimo]
            gasto = (Decimal(self.km(dias_desde_o_dia_1) - self.km(ultimo))
                     / consumo[combustivel_no_tanque])
            nivel = int(((capacidade - gasto) / capacidade * 8).to_integral_value(ROUND_HALF_UP))
            self.enviar(paula, "POST", f"/veiculos/{v}/tanque/marcacoes", {
                "data": primeiro.isoformat(), "quilometragem": self.km(dias_desde_o_dia_1),
                "nivel": max(0, min(8, nivel))})

    def _manutencoes_civic(self, paula: TestClient, v: int) -> None:
        oleo = self.enviar(paula, "POST", f"/veiculos/{v}/planos", {
            "nome": "Troca de óleo e filtro", "sistema": "motor",
            "intervalo_km": 10000, "intervalo_meses": 12,
            "data_base": self.dia(230), "km_base": self.km(230)})
        self.enviar(paula, "POST", f"/veiculos/{v}/planos", {
            "nome": "Rodízio de pneus", "sistema": "pneus", "intervalo_km": 7500,
            "data_base": self.dia(210), "km_base": self.km(210)})
        self.enviar(paula, "POST", f"/veiculos/{v}/planos", {
            "nome": "Correia dentada", "sistema": "motor", "intervalo_km": 60000,
            "intervalo_meses": 48, "data_base": "2023-01-20", "km_base": 31000})

        self.enviar(paula, "POST", f"/veiculos/{v}/manutencoes", {
            "descricao": "Troca de óleo e filtro", "sistema": "motor", "status": "realizada",
            "data": self.dia(205), "quilometragem": self.km(205), "oficina": "Oficina do Zé",
            "plano_id": oleo["id"],
            "itens": [
                {"tipo": "peca", "nome": "Óleo 0W20 sintético (4 L)", "valor": "219.60"},
                {"tipo": "peca", "nome": "Filtro de óleo", "valor": "39.90"},
                {"tipo": "mao_de_obra", "nome": "Troca", "valor": "60.00"},
            ]})
        freios = self.enviar(paula, "POST", f"/veiculos/{v}/manutencoes", {
            "descricao": "Pastilhas de freio dianteiras", "sistema": "freios",
            "status": "realizada", "data": self.dia(125), "quilometragem": self.km(125),
            "oficina": "Freios & Cia",
            "garantia_ate": (self.hoje + timedelta(days=240)).isoformat(),
            "garantia_km": self.km(125) + 20000,
            "itens": [
                {"tipo": "peca", "nome": "Jogo de pastilhas dianteiras", "valor": "189.00"},
                {"tipo": "mao_de_obra", "nome": "Instalação e sangria", "valor": "120.00"},
            ]})
        self.foto(paula, v, "Nota fiscal das pastilhas", (90, 90, 90), 125,
                  manutencao_id=freios["id"])
        self.enviar(paula, "POST", f"/veiculos/{v}/manutencoes", {
            "descricao": "Alinhamento e balanceamento", "sistema": "pneus",
            "status": "realizada", "data": self.dia(62), "quilometragem": self.km(62),
            "valor": "150.00", "oficina": "Pneus Express"})
        self.enviar(paula, "POST", f"/veiculos/{v}/manutencoes", {
            "descricao": "Revisão dos 90 mil km", "sistema": "outros", "status": "agendada",
            "data": (self.hoje + timedelta(days=18)).isoformat(),
            "oficina": "Concessionária Honda", "valor": "980.00"})

        # Problemas: um resolvido pela manutenção dos freios, um em aberto e um descartado.
        rangido = self.enviar(paula, "POST", f"/veiculos/{v}/diagnosticos", {
            "titulo": "Rangido ao frear", "sistema": "freios", "gravidade": "alta",
            "descricao": "Barulho metálico nas freadas mais fortes.",
            "data_identificacao": self.dia(131), "quilometragem": self.km(131)})
        self.enviar(paula, "POST", f"/veiculos/{v}/diagnosticos/{rangido['id']}/vincular",
                    {"manutencao_id": freios["id"]})
        barulho = self.enviar(paula, "POST", f"/veiculos/{v}/diagnosticos", {
            "titulo": "Barulho na suspensão dianteira", "sistema": "suspensao",
            "gravidade": "media", "descricao": "Estalo em lombadas, lado direito.",
            "data_identificacao": self.dia(20), "quilometragem": self.km(20)})
        self.enviar(paula, "POST", f"/veiculos/{v}/diagnosticos/{barulho['id']}/notas", {
            "texto": "Piora com o carro frio. Marcar avaliação na oficina.",
            "data": self.dia(9)})
        self.foto(paula, v, "Suspensão dianteira direita", (60, 70, 80), 19,
                  diagnostico_id=barulho["id"])
        luz = self.enviar(paula, "POST", f"/veiculos/{v}/diagnosticos", {
            "titulo": "Luz da injeção acendeu", "sistema": "motor", "gravidade": "baixa",
            "data_identificacao": self.dia(88), "quilometragem": self.km(88)})
        self.enviar(paula, "POST", f"/veiculos/{v}/diagnosticos/{luz['id']}/descartar", {
            "motivo": "Tampa do tanque mal fechada; a luz apagou depois de dois dias.",
            "data": self.dia(86)})

    def _gastos_civic(self, paula: TestClient, v: int) -> None:
        pagos = [
            ("ipva", "2340.00", "IPVA (cota única)", 215),
            ("licenciamento", "160.22", "Licenciamento anual", 190),
            ("seguro", "2890.00", "Seguro anual", 170),
            ("lavagem", "60.00", "Lavagem completa", 75),
            ("pedagio", "38.40", "Viagem para o litoral", 45),
            ("estacionamento", "25.00", "Shopping", 33),
            ("lavagem", "45.00", "Lavagem simples", 6),
            ("estacionamento", "18.00", "Centro", 2),
        ]
        no_mes = (self.hoje - self.hoje.replace(day=1)).days
        for categoria, valor, descricao, dias in pagos:
            if dias <= 6:  # os gastos pequenos ficam dentro do mês atual
                dias = min(dias, no_mes)
            self.enviar(paula, "POST", f"/veiculos/{v}/gastos", {
                "categoria": categoria, "valor": valor, "descricao": descricao,
                "data": self.dia(dias), "pago": True, "data_pagamento": self.dia(dias)})
        # Uma conta vencida (aparece em "Precisa de atenção") e gastos futuros.
        self.enviar(paula, "POST", f"/veiculos/{v}/gastos", {
            "categoria": "multa", "valor": "130.16", "descricao": "Multa por estacionar em local proibido",
            "data": self.dia(40), "pago": False, "data_vencimento": self.dia(5)})
        self.enviar(paula, "POST", f"/veiculos/{v}/gastos", {
            "categoria": "acessorios", "valor": "149.90", "descricao": "Tapetes (parcelado no cartão)",
            "data": self.dia(1), "pago": False,
            "data_vencimento": (self.hoje + timedelta(days=12)).isoformat()})
        # Gastos futuros: IPVA do ano que vem e a renovação do seguro.
        self.enviar(paula, "POST", f"/veiculos/{v}/gastos", {
            "categoria": "ipva", "valor": "1645.00", "descricao": f"IPVA {self.hoje.year + 1}",
            "data": self.dia(0), "pago": False,
            "data_vencimento": date(self.hoje.year + 1, 5, 13).isoformat()})
        self.enviar(paula, "POST", f"/veiculos/{v}/gastos", {
            "categoria": "seguro", "valor": "2980.00", "descricao": "Renovação do seguro",
            "data": self.dia(0), "pago": False,
            "data_vencimento": (self.hoje + timedelta(days=195)).isoformat()})

    def _projetos_civic(self, paula: TestClient, v: int) -> None:
        som = self.enviar(paula, "POST", f"/veiculos/{v}/projetos", {
            "nome": "Som novo", "categoria": "som", "orcamento": "1500.00",
            "descricao": "Central multimídia com CarPlay e alto-falantes dianteiros.",
            "status": "em_andamento"})
        self.foto(paula, v, "Painel com o rádio original", (70, 60, 50), 100,
                  projeto_id=som["id"], momento="antes")
        for descricao, valor, dias in (("Central multimídia", "980.00", 98),
                                       ("Alto-falantes dianteiros", "320.00", 98),
                                       ("Instalação", "150.00", 96)):
            self.enviar(paula, "POST", f"/veiculos/{v}/projetos/{som['id']}/itens",
                        {"descricao": descricao, "data": self.dia(dias), "valor": valor})
        self.foto(paula, v, "Central multimídia instalada", (20, 40, 70), 95,
                  projeto_id=som["id"], momento="depois")
        self.enviar(paula, "POST", f"/veiculos/{v}/projetos/{som['id']}/concluir",
                    {"data_conclusao": self.dia(95)})

        pelicula = self.enviar(paula, "POST", f"/veiculos/{v}/projetos", {
            "nome": "Película nos vidros", "categoria": "exterior", "orcamento": "400.00",
            "status": "em_andamento",
            "data_prevista": (self.hoje + timedelta(days=10)).isoformat()})
        self.enviar(paula, "POST", f"/veiculos/{v}/projetos/{pelicula['id']}/itens",
                    {"descricao": "Película G20 (vidros laterais e traseiro)", "data": self.dia(8),
                     "valor": "450.00"})
        self.enviar(paula, "POST", f"/veiculos/{v}/projetos", {
            "nome": "Rodas aro 17", "categoria": "exterior", "status": "planejado",
            "descricao": "Pesquisar preço de rodas e pneus 215/50 R17."})

    # ------------------------------------------------------------- outros
    def moto(self, paula: TestClient) -> None:
        moto = self.enviar(paula, "POST", "/veiculos", {
            "marca": "Honda", "modelo": "CG 160 Fan", "versao": None, "ano": 2021,
            "placa": "QTE4F21", "cor": "Vermelha", "tipo_combustivel": "flex",
            "quilometragem": 18400, "data_aquisicao": None, "valor_aquisicao": None,
            "km_aquisicao": None, "capacidade_tanque": "14.0"})
        m = moto["id"]
        self.resumo.veiculos += 1
        for dias, km, litros in ((40, 17700, "9.000"), (21, 18050, "8.900"), (4, 18380, "8.700")):
            self.enviar(paula, "POST", f"/veiculos/{m}/abastecimentos", {
                "combustivel": "gasolina", "tipo": "comum", "data": self.dia(dias),
                "quilometragem": km, "litros": litros, "valor_litro": "6.190",
                "tanque_cheio": True, "posto": "Posto Ipiranga Centro"})

    def argo(self, rafael: TestClient) -> None:
        argo = self.enviar(rafael, "POST", "/veiculos", {
            "marca": "Fiat", "modelo": "Argo", "versao": "Drive 1.0", "ano": 2022,
            "placa": "ABC1D23", "cor": "Branco", "tipo_combustivel": "flex",
            "quilometragem": 31200, "data_aquisicao": "2023-06-10",
            "valor_aquisicao": "68900.00", "km_aquisicao": 9800, "capacidade_tanque": "47.0"})
        a = argo["id"]
        self.resumo.veiculos += 1
        for dias, km, litros in ((30, 30300, "35.000"), (15, 30760, "33.800"), (2, 31150, "29.400")):
            self.enviar(rafael, "POST", f"/veiculos/{a}/abastecimentos", {
                "combustivel": "etanol", "tipo": "comum", "data": self.dia(dias),
                "quilometragem": km, "litros": litros, "valor_litro": "4.190",
                "tanque_cheio": True, "posto": "Posto BR Rodovia"})
        self.enviar(rafael, "POST", f"/veiculos/{a}/gastos", {
            "categoria": "seguro", "valor": "1980.00", "descricao": "Seguro anual",
            "data": self.dia(60), "pago": True, "data_pagamento": self.dia(60)})


def carregar(engine: Engine, hoje: date | None = None) -> Resumo:
    """Grava os dados de exemplo no banco da engine (que precisa estar migrado e sem contas)."""
    carga = _Carga(hoje or calendario.hoje())
    app.dependency_overrides[obter_engine] = lambda: engine
    try:
        paula = carga.conta("Paula Demonstração", EMAIL_ADMIN)
        rafael = carga.conta("Rafael Demonstração", EMAIL_PADRAO)
        carga.resumo.contas = [EMAIL_ADMIN, EMAIL_PADRAO]
        carga.moto(paula)
        carga.civic(paula)
        veiculos = carga.enviar(paula, "GET", "/veiculos")
        civic = next(v for v in veiculos if v["placa"] == "BRA2E19")
        carga.enviar(paula, "POST", f"/veiculos/{civic['id']}/selecionar")
        carga.argo(rafael)
    finally:
        app.dependency_overrides.pop(obter_engine, None)
    with abrir_sessao(engine) as sessao:
        UsuarioService(UnidadeDeTrabalho(sessao), UsuarioRepository(sessao)).promover_a_admin(EMAIL_ADMIN)
    return carga.resumo
