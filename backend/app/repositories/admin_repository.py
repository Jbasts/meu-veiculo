"""Consultas da área de administração: usuários (view vw_usuario_resumo, do SQL
original, que já deixa senha_hash de fora) e veículos de todos os donos.

Busca: o texto digitado procura em parte do nome ou do e-mail (veículos: marca,
modelo, placa ou nome do dono), sem diferenciar maiúsculas. Os caracteres
% e _ digitados são tratados como texto, não como curinga.

Ordem estável para a paginação: nome e id (usuários); nome do dono, id do dono
e id do veículo (veículos). Assim nenhuma linha se repete nem some entre páginas.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.entities.usuario import UsuarioResumo
from app.entities.veiculo import VeiculoComDono

SQL_FILTRO_USUARIOS = """
     WHERE (CAST(:busca AS text) IS NULL
            OR r.nome ILIKE :busca ESCAPE '\\' OR r.email ILIKE :busca ESCAPE '\\')
"""

SQL_USUARIOS = text(f"""
    SELECT r.id, r.nome, r.email, r.perfil, r.ativo, r.ultimo_acesso, r.criado_em,
           r.veiculos AS veiculos_ativos,
           (SELECT COUNT(*) FROM veiculo v WHERE v.usuario_id = r.id) AS veiculos
      FROM vw_usuario_resumo r
      {SQL_FILTRO_USUARIOS}
       AND (CAST(:perfil AS text) IS NULL OR r.perfil = :perfil)
     ORDER BY lower(r.nome), r.id
     LIMIT :limite OFFSET :deslocamento
""")

SQL_CONTAGEM_POR_PERFIL = text(f"""
    SELECT r.perfil, COUNT(*) AS quantidade
      FROM vw_usuario_resumo r
      {SQL_FILTRO_USUARIOS}
     GROUP BY r.perfil
""")

SQL_USUARIO = text("""
    SELECT r.id, r.nome, r.email, r.perfil, r.ativo, r.ultimo_acesso, r.criado_em,
           r.veiculos AS veiculos_ativos,
           (SELECT COUNT(*) FROM veiculo v WHERE v.usuario_id = r.id) AS veiculos
      FROM vw_usuario_resumo r
     WHERE r.id = :usuario_id
""")

SQL_FILTRO_VEICULOS = """
      FROM veiculo v
      JOIN usuario u ON u.id = v.usuario_id
     WHERE (CAST(:busca AS text) IS NULL
            OR v.marca ILIKE :busca ESCAPE '\\' OR v.modelo ILIKE :busca ESCAPE '\\'
            OR v.placa ILIKE :busca_placa ESCAPE '\\' OR u.nome ILIKE :busca ESCAPE '\\')
       AND (CAST(:usuario_id AS int) IS NULL OR v.usuario_id = :usuario_id)
"""

SQL_VEICULOS = text(f"""
    SELECT v.id, v.usuario_id, v.marca, v.modelo, v.ano, v.placa, v.ativo,
           u.nome AS dono_nome, u.ativo AS dono_ativo
      {SQL_FILTRO_VEICULOS}
     ORDER BY lower(u.nome), u.id, v.ativo DESC, v.id
     LIMIT :limite OFFSET :deslocamento
""")

SQL_CONTAR_VEICULOS = text(f"SELECT COUNT(*) {SQL_FILTRO_VEICULOS}")


def padrao_de_busca(busca: str | None) -> str | None:
    """'gol_1' -> '%gol\\_1%' (o que foi digitado é procurado como texto)."""
    if not busca:
        return None
    escapado = busca.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escapado}%"


class AdminRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def usuarios(self, busca: str | None, perfil: str | None, limite: int,
                 deslocamento: int) -> list[UsuarioResumo]:
        linhas = self._sessao.execute(SQL_USUARIOS, {
            "busca": padrao_de_busca(busca), "perfil": perfil, "limite": limite,
            "deslocamento": deslocamento}).mappings()
        return [UsuarioResumo(**linha) for linha in linhas]

    def contagem_por_perfil(self, busca: str | None) -> dict[str, int]:
        linhas = self._sessao.execute(SQL_CONTAGEM_POR_PERFIL, {"busca": padrao_de_busca(busca)})
        return {linha.perfil: linha.quantidade for linha in linhas}

    def usuario(self, usuario_id: int) -> UsuarioResumo | None:
        linha = self._sessao.execute(SQL_USUARIO, {"usuario_id": usuario_id}).mappings().first()
        return UsuarioResumo(**linha) if linha else None

    def _parametros_veiculos(self, busca: str | None, usuario_id: int | None) -> dict:
        padrao = padrao_de_busca(busca)
        # A placa é guardada sem hífen e sem espaços: "abc-1234" acha "ABC1234".
        placa = padrao_de_busca("".join(busca.split()).replace("-", "")) if busca else None
        return {"busca": padrao, "busca_placa": placa or padrao, "usuario_id": usuario_id}

    def veiculos(self, busca: str | None, usuario_id: int | None, limite: int,
                 deslocamento: int) -> list[VeiculoComDono]:
        linhas = self._sessao.execute(SQL_VEICULOS, {
            **self._parametros_veiculos(busca, usuario_id), "limite": limite,
            "deslocamento": deslocamento}).mappings()
        return [VeiculoComDono(**linha) for linha in linhas]

    def contar_veiculos(self, busca: str | None, usuario_id: int | None) -> int:
        return self._sessao.execute(
            SQL_CONTAR_VEICULOS, self._parametros_veiculos(busca, usuario_id)).scalar() or 0
