"""Sessão do banco (SQLAlchemy) e controle de transação.

- Cada requisição da API recebe uma sessão própria (veja app/dependencias.py).
- Os repositories fazem as consultas usando essa sessão.
- Os services decidem onde começa e termina uma transação, usando
  UnidadeDeTrabalho.transacao(). Tudo o que for feito dentro do bloco é
  gravado junto; se qualquer parte falhar, nada é gravado.

Exemplo (etapa 5): criar a manutenção e resolver o diagnóstico precisam
acontecer na mesma transação:

    with self.uow.transacao():
        manutencao = self.manutencoes.criar(...)
        self.diagnosticos.resolver(diagnostico_id, manutencao.id)
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session


def abrir_sessao(engine: Engine) -> Session:
    return Session(engine, expire_on_commit=False, autoflush=False)


class UnidadeDeTrabalho:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    @contextmanager
    def transacao(self) -> Iterator[None]:
        try:
            yield
            self._sessao.commit()
        except BaseException:
            self._sessao.rollback()
            raise
