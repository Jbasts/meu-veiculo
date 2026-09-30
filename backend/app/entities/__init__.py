"""Entities: o que o sistema representa (tabelas mapeadas e objetos de domínio).

Os imports abaixo registram todas as tabelas mapeadas em Base.metadata
(o tests/test_entities.py confere cada uma com o banco).
"""

from app.entities.leitura_km import LeituraKm
from app.entities.manutencao import Manutencao, ManutencaoItem, PlanoManutencao
from app.entities.recuperacao_senha import RecuperacaoSenha
from app.entities.sessao import Sessao
from app.entities.tentativa_acesso import TentativaAcesso
from app.entities.usuario import Usuario
from app.entities.veiculo import Veiculo
from app.entities.veiculo_foto import VeiculoFoto

__all__ = ["LeituraKm", "Manutencao", "ManutencaoItem", "PlanoManutencao", "RecuperacaoSenha",
           "Sessao", "TentativaAcesso", "Usuario", "Veiculo", "VeiculoFoto"]
