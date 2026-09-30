"""Entities: o que o sistema representa (tabelas mapeadas e objetos de domínio).

Os imports abaixo registram todas as tabelas mapeadas em Base.metadata
(o tests/test_entities.py confere cada uma com o banco).
"""

from app.entities.recuperacao_senha import RecuperacaoSenha
from app.entities.sessao import Sessao
from app.entities.tentativa_acesso import TentativaAcesso
from app.entities.usuario import Usuario

__all__ = ["RecuperacaoSenha", "Sessao", "TentativaAcesso", "Usuario"]
