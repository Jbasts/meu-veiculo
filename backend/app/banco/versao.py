"""O banco está na versão que este código espera?

Se o código foi atualizado (por exemplo, uma migration nova) e o banco não,
as consultas falham no meio do uso com erros confusos ("coluna ... não
existe"). Antes disso, a API confere a versão e, se estiver atrasada,
responde com uma mensagem clara (HTTP 503; veja app/dependencias.py).

Só o resultado "em dia" fica guardado (a conferência não se repete a cada
requisição). Enquanto o banco estiver desatualizado, a conferência é
refeita: basta rodar "gerenciar.py migrar" com o backend ligado.
Se o banco for voltado para uma versão anterior com o backend ligado,
reinicie o backend.
"""

from alembic.script.revision import RevisionError
from alembic.util import CommandError
from sqlalchemy import Engine

from app.banco.migracoes import ler_estado

COMANDO_MIGRAR = r".\.venv\Scripts\python.exe gerenciar.py migrar"

_em_dia: set[str] = set()


def problema_de_versao(engine: Engine) -> str | None:
    """None se o banco está na versão do código; senão, a explicação para a pessoa."""
    chave = engine.url.render_as_string(hide_password=True)
    if chave in _em_dia:
        return None
    try:
        estado = ler_estado(engine)
    except (RevisionError, CommandError):
        # A versão gravada no banco não existe neste código (banco mais novo que o código).
        return ("O banco de dados está numa versão que este código não conhece. "
                "Atualize o código do sistema ou restaure o backup correspondente.")
    if estado.situacao == "sem_controle":
        return ("O banco de dados foi criado sem o controle de versões. "
                "Veja no README como usar \"gerenciar.py adotar-banco-existente\".")
    if estado.pendentes:
        atual = estado.versao_atual or "vazio"
        return (f"O banco de dados está na versão {atual} e o sistema precisa da "
                f"{estado.versao_mais_recente}. Na pasta backend, rode: {COMANDO_MIGRAR}")
    _em_dia.add(chave)
    return None


def esquecer_conferencias() -> None:
    """Faz a próxima requisição conferir de novo (usado nos testes)."""
    _em_dia.clear()
