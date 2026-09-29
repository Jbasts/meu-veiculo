"""Backup do banco com pg_dump (formato "custom", restaurável com pg_restore).

A senha vai para o pg_dump pela variável de ambiente PGPASSWORD do processo
filho, e não pela linha de comando, para não aparecer na lista de processos.
"""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.config import FUSO_HORARIO, Configuracoes, obter_configuracoes


class BackupFalhou(Exception):
    pass


def localizar_programa(nome: str, cfg: Configuracoes | None = None) -> Path:
    cfg = cfg or obter_configuracoes()
    executavel = f"{nome}.exe" if os.name == "nt" else nome
    candidatos: list[Path] = []
    if cfg.pg_bin:
        candidatos.append(Path(cfg.pg_bin) / executavel)
    no_path = shutil.which(nome)
    if no_path:
        candidatos.append(Path(no_path))
    if os.name == "nt":
        raiz = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "PostgreSQL"
        if raiz.is_dir():
            versoes = sorted(
                (p for p in raiz.iterdir() if p.name.isdigit()),
                key=lambda p: int(p.name),
                reverse=True,
            )
            candidatos += [p / "bin" / executavel for p in versoes]
    for candidato in candidatos:
        if candidato.is_file():
            return candidato
    raise BackupFalhou(
        f"Não encontrei o programa {executavel}. Informe a pasta 'bin' do PostgreSQL "
        "em PG_BIN no backend/.env (ex.: C:\\Program Files\\PostgreSQL\\16\\bin)."
    )


def fazer_backup(nome_banco: str | None = None, motivo: str = "manual",
                 cfg: Configuracoes | None = None) -> Path:
    cfg = cfg or obter_configuracoes()
    nome_banco = nome_banco or cfg.db_nome
    pg_dump = localizar_programa("pg_dump", cfg)
    cfg.pasta_backups.mkdir(parents=True, exist_ok=True)
    agora = datetime.now(ZoneInfo(FUSO_HORARIO)).strftime("%Y%m%d_%H%M%S")
    destino = cfg.pasta_backups / f"{nome_banco}_{agora}_{motivo}.dump"
    ambiente = dict(os.environ, PGPASSWORD=cfg.db_senha.get_secret_value())
    resultado = subprocess.run(
        [
            str(pg_dump),
            "--format=custom",
            f"--host={cfg.db_host}",
            f"--port={cfg.db_porta}",
            f"--username={cfg.db_usuario}",
            f"--file={destino}",
            nome_banco,
        ],
        env=ambiente,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if resultado.returncode != 0:
        destino.unlink(missing_ok=True)
        raise BackupFalhou(f"O pg_dump falhou: {resultado.stderr.strip()}")
    return destino
