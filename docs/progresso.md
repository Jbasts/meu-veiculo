# Progresso do projeto Meu Veículo

Status possíveis: **pendente**, **em andamento**, **entregue** (código pronto e testes do Claude executados, aguardando a Paula) e **validada** (a Paula testou no computador dela).

| Etapa | Objetivo | Status |
|---|---|---|
| 0 | Análise dos anexos, escolha da plataforma e plano de etapas | validada |
| 1 | Estrutura de pastas, banco, migrations e ambiente | pendente |
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
