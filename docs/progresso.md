# Progresso do projeto Meu Veículo

Status possíveis: **pendente**, **em andamento**, **entregue** (código pronto e testes do Claude executados, aguardando a Paula) e **validada** (a Paula testou no computador dela).

| Etapa | Objetivo | Status |
|---|---|---|
| 0 | Análise dos anexos, escolha da plataforma e plano de etapas | validada |
| 1 | Estrutura de pastas, banco, migrations e ambiente | validada |
| 2 | Cadastro, login, recuperação de senha e permissões | pendente |
| 3 | Veículos, quilometragem e base das fotos (upload, capa e galeria) | pendente |
| 4 | Manutenções e planos (inclui fotos ligadas a manutenção) | pendente |
| 5 | Diagnósticos (inclui fotos ligadas a diagnóstico) | pendente |
| 6 | Gastos e finanças | pendente |
| 7 | Abastecimentos e consumo | pendente |
| 8 | Projetos e fotos de antes/depois | pendente |
| 9 | Histórico, tela inicial e administração | pendente |
| 10 | Revisão integrada, acesso pelo celular e README final | pendente |

A ordem pode ser ajustada na etapa 0 para respeitar dependências; registre o motivo em `decisoes.md`.

## Registro por etapa

<!-- O Claude acrescenta aqui, ao fim de cada etapa:
### Etapa N — título (data)
- Ficou funcionando:
- Arquivos criados/alterados:
- Testes executados (comando e resultado):
- Depende de validação da Paula:
- Pendências para a próxima etapa:
-->

### Etapa 0 — Análise dos anexos, escolha da plataforma e plano de etapas (29/09/2026)
- Ficou pronto: análise completa do SQL, do PDF e de `observacoes-anexos.md` (todas as observações confirmadas); lista de inconsistências do banco e das correções por migration; comparação PWA × app multiplataforma; stack recomendada; plano de etapas com ajuste de ordem (base das fotos na etapa 3). Nenhum código foi escrito.
- Decisões aprovadas pela Paula: PWA; React + TypeScript, FastAPI e PostgreSQL; testes em Android com Chrome; "tipos de veículo" = `tipo_combustivel`; arredondamento meio para cima; "+" do admin envia link para definir senha. Detalhes em `decisoes.md`.
- Arquivos alterados: `docs/decisoes.md`, `docs/progresso.md`.
- Testes executados: nenhum (etapa sem código).
- Status "validada": a Paula revisou a análise e aprovou as decisões em 29/09/2026; não havia nada a executar.
- Pendências para a próxima etapa:
  - Conferir as versões instaladas (Python, Node.js, PostgreSQL e Git). As chaves estrangeiras compostas com `ON DELETE SET NULL (coluna)` exigem PostgreSQL 15 ou mais novo; em versão anterior, a mesma regra será feita por trigger.
  - Criar bancos separados de desenvolvimento e de teste e a migration 0001 (SQL original sem alterações), com o caminho de instalação em banco vazio separado do registro em banco existente.
  - Fixar o fuso `America/Sao_Paulo` nas conexões do backend.
  - Propostas técnicas a confirmar quando forem implementadas: Alembic com migrations em SQL, Argon2id para senhas, sessão em cookie `httpOnly`, Mailpit para e-mail local, `data_pagamento` em gasto, base fixa (`data_base`/`km_base`) nos planos, tabela `leitura_km`, `garantia_km` como limite absoluto do hodômetro, agrupamento "Documentação" = IPVA + licenciamento.

### Etapa 1 — Estrutura, banco, migrations e ambiente (29/09/2026)
- Ambiente conferido: Python 3.13.15, Node 24.16.0/npm 10.8.1, Git 2.44, PostgreSQL 16.2 (serviço `postgresql-x64-16`).
- Ficou funcionando: backend em camadas (routes → controllers → services → repositories → banco, com entities e schemas), reorganizado assim a pedido da Paula; Alembic com a 0001 (SQL original conferido por SHA-256); `gerenciar.py` (criar-bancos, estado, migrar, adotar-banco-existente, backup); usuário `meu_veiculo_app` sem superusuário; bancos `meu_veiculo` (na versão 0001) e `meu_veiculo_teste`; fuso `America/Sao_Paulo` nas conexões; `GET /api/saude`; frontend React + TypeScript (pages, components, services, types, utils, styles) com a tela "Situação do sistema" e proxy `/api` do Vite; README com arquitetura, instalação, backup e problemas comuns.
- Arquivos criados/alterados: `backend/` (app, migrations, tests, gerenciar.py, alembic.ini, pytest.ini, requirements*.txt, .env.example), `frontend/` (src, index.html, vite.config.ts, tsconfig.json, package*.json, public/icone.svg), `README.md`, `.gitignore` (acréscimo de backups e tsbuildinfo), `CLAUDE.md`, `docs/decisoes.md`, `docs/progresso.md`.
- Testes executados pelo Claude:
  - `.\.venv\Scripts\python.exe -m pytest` (backend): 61 passaram, 0 falharam (PostgreSQL de teste).
  - `npm test` (frontend): 11 passaram, 0 falharam; `npm run typecheck` sem erros; `npm run build` ok.
  - `gerenciar.py estado`: banco de desenvolvimento na 0001, sem pendências.
  - `GET http://127.0.0.1:8000/api/saude` → 200; Vite iniciado → página 200 e `/api/saude` pelo proxy → 200.
- Validado pela Paula no computador dela: preencheu `DB_SENHA`, rodou `criar-bancos` e `migrar`, 61 testes passando, backend com `/api/saude` 200 e frontend rodando. Não havia banco anterior criado com o SQL original, então o caminho `adotar-banco-existente` foi validado só pelos testes automáticos.
- Não coberto nesta etapa: o backup automático antes de migrar um banco que já tem migrations só é exercitado quando existir a 0002 (a função de backup em si foi testada); acesso pelo celular (etapa 10); PWA instalável (depois do login).
- Pendências para a próxima etapa (2 — cadastro, login, recuperação de senha e permissões): primeira migration nova (0002) com tabelas de sessão e de recuperação de senha e normalização/`trim` do e-mail (com verificação prévia de duplicatas); entity `Usuario`; definir Argon2id, cookie `httpOnly`, limite de tentativas e Mailpit para o e-mail local; rotas do frontend (React Router).
