# Progresso do projeto Meu Veículo

Status possíveis: **pendente**, **em andamento**, **entregue** (código pronto e testes do Claude executados, aguardando a Paula) e **validada** (a Paula testou no computador dela).

| Etapa | Objetivo | Status |
|---|---|---|
| 0 | Análise dos anexos, escolha da plataforma e plano de etapas | validada |
| 1 | Estrutura de pastas, banco, migrations e ambiente | validada |
| 2 | Cadastro, login, recuperação de senha e permissões | validada |
| 3 | Veículos, quilometragem e base das fotos (upload, capa e galeria) | validada |
| 4 | Manutenções e planos (inclui fotos ligadas a manutenção) | validada |
| 5 | Diagnósticos (inclui fotos ligadas a diagnóstico) | entregue |
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

### Etapa 2 — Cadastro, login, recuperação de senha e permissões (29/09/2026)
- Ficou funcionando (código + testes do Claude):
  - Migration 0002: e-mail normalizado com CHECK (lista colisões e para sem alterar nada), tabelas `sessao`, `recuperacao_senha` e `tentativa_acesso`, trigger que protege o último admin ativo (com trava para alterações simultâneas).
  - Backend em camadas: entities `Usuario`, `Sessao`, `RecuperacaoSenha`, `TentativaAcesso`; repositories, `AutenticacaoService`, `SenhaService` (Argon2id + política), `UsuarioService`, `email_service` (modo arquivo/smtp), `AuthController`, `auth_routes` (`/api/auth/cadastro`, `entrar`, `sair`, `eu`, `alterar-senha`, `recuperar-senha`, `redefinir-senha`), `SessaoAtualDep`/`AdminDep`, proteção CSRF por cabeçalho, erros de formato em português.
  - `gerenciar.py promover-admin EMAIL` (primeiro admin).
  - Frontend: Entrar, Criar conta, Esqueci minha senha, Redefinir senha, Conta e senha, Início provisório, rotas protegidas, `AuthContext`, validação local + erros do servidor por campo, trava contra envio duplicado.
- Arquivos criados/alterados: `backend/app/{config.py, dependencias.py, entities/*, repositories/*, services/*, controllers/*, routes/*, schemas/*, banco/migracoes.py}`, `backend/migrations/versions/0002_autenticacao.py`, `backend/gerenciar.py`, `backend/requirements.txt`, `backend/.env.example`, `backend/tests/*`; `frontend/src/{App.tsx, pages/*, components/*, contexts/*, hooks/*, services/*, types/usuario.ts, utils/validacao.ts, styles/tema.css, tests/*}`, `frontend/vite.config.ts`, `frontend/package*.json`; `.gitignore`, `README.md` (seções 9 e 10), `CLAUDE.md`, `docs/decisoes.md`, `docs/progresso.md`.
- Testes executados pelo Claude:
  - `.\.venv\Scripts\python.exe -m pytest` (backend): 134 passaram, 0 falharam (inclui link consumido por duas threads ao mesmo tempo, falha forçada que desfaz o consumo do link, duas desativações simultâneas do último admin, backup automático antes de migrar).
  - `npm test` (frontend): 30 passaram, 0 falharam; `npm run typecheck` sem erros; `npm run build` ok.
  - Fluxo real com uvicorn no banco de TESTE (17 passos: cadastro, sessão em dois "aparelhos", 409, 422 para `perfil`, 403 sem cabeçalho, recuperação com `.eml` gravado, redefinição, reuso recusado, sessões encerradas, senha antiga recusada, nova aceita, sair). Esse teste achou e permitiu corrigir o link quebrado no `.eml` (codificação quoted-printable → 8bit no modo arquivo). Log do servidor sem senha nem token.
- Depende de validação da Paula:
  - Rodar `gerenciar.py migrar` no banco de desenvolvimento (ele está na 0001; o `migrar` faz backup antes).
  - Testar as telas no navegador do computador (criar conta, sair, entrar, trocar senha, recuperar pelo `.eml`, `promover-admin`).
  - Envio real por SMTP (e Mailpit) não foi testado: depende da conta de e-mail dela.
  - Celular (Android/Chrome) fica para a etapa 10.
- Validado pela Paula no computador dela (30/09/2026): aplicou a 0002 no banco de desenvolvimento e testou as telas de conta; relatou que tudo funcionou. O pedido de recuperação gravou o `.eml` em `backend\emails_dev\` (modo arquivo, padrão), mas nenhum e-mail chegou à caixa de entrada, o que é o esperado nesse modo.
- Pendência adiada a pedido da Paula: configurar e testar o envio real por SMTP (README, seção 10.2). O código existe, mas nunca foi testado com um provedor de verdade.
- Pendências para a próxima etapa (3 — veículos, quilometragem e base das fotos): entity `Veiculo`, normalização de placa com detecção de colisões, tabela `leitura_km`, correção de km, verificação de propriedade em todo acesso (usando `SessaoAtualDep`), upload de fotos com validação de conteúdo, barra de navegação inferior.

### Etapa 3 — Veículos, quilometragem e base das fotos (30/09/2026)
- Ficou funcionando (código + testes do Claude):
  - Migration 0003: placa normalizada com CHECK (lista colisões por dono e para sem alterar nada); tabela `leitura_km` (data da leitura separada da data de digitação, anulação com motivo); `veiculo.data_leitura_km`; quilometragem atual calculada pelo banco como a maior leitura válida; triggers novos de abastecimento/manutenção/diagnóstico (agendada não conta; mudança só de status para realizada conta; editar ou apagar o registro recalcula); proteção contra alterar `veiculo.quilometragem` direto; `usuario.veiculo_em_uso_id` com chave composta (só veículo do próprio usuário). Dados antigos: registros viram leituras com as datas deles; km sem origem vira leitura "legado" sem data.
  - Backend: entities `Veiculo`, `LeituraKm`, `VeiculoFoto`; repositories (inclui `ArquivoFotoRepository` para a pasta de fotos); `VeiculoService`, `QuilometragemService`, `FotoService`, `imagem_service` (Pillow + pillow-heif), `acesso_veiculo` (regra única de permissão); `veiculo_routes` com 19 endpoints em `/api/veiculos/...`; limite de tamanho de requisição (HTTP 413); `gerenciar.py limpar-fotos`.
  - Frontend: barra de navegação inferior; Início com veículo em uso e hodômetro; Mais; Meus veículos; cadastro e edição de veículo (com foto de capa); Meu veículo; Quilometragem (nova leitura, histórico, corrigir, anular); galeria, nova foto (câmera ou galeria), detalhe da foto (legenda, data, capa, apagar); diálogo de confirmação para inativar, anular e apagar; volta para Entrar quando a sessão termina no meio do uso.
- Arquivos criados/alterados: `backend/migrations/versions/0003_veiculos_e_quilometragem.py`; `backend/app/{config.py, dependencias.py, main.py}`; `backend/app/entities/{veiculo, leitura_km, veiculo_foto, usuario, __init__}.py`; `backend/app/repositories/{veiculo, leitura_km, foto, arquivo_foto}_repository.py` e `erros.py`; `backend/app/services/{veiculo_service, quilometragem_service, foto_service, imagem_service, acesso_veiculo, calendario, paginacao}.py`; `backend/app/schemas/veiculo_schema.py`; `backend/app/controllers/{veiculo_controller, foto_controller, limite_corpo, erros_http}.py`; `backend/app/routes/{veiculo_routes, __init__}.py`; `backend/gerenciar.py`, `backend/requirements.txt`, `backend/.env.example`; `backend/tests/{veiculo_utils, test_migracao_0003, test_veiculos_api, test_quilometragem_api, test_fotos_api, test_migracoes}.py`. `frontend/src/{App.tsx, main.tsx}`; `pages/{Inicio, Mais, Veiculos, VeiculoForm, VeiculoDetalhe, Quilometragem, Fotos, FotoNova, FotoDetalhe, EmBreve, Conta}Page.tsx` e `Veiculos.test.tsx`; `components/{BarraNavegacao, Icones, PecasVeiculo, Formulario, EstadoDaTela, TopoComVoltar}.tsx`; `contexts/{VeiculosContext, AuthContext}.tsx`; `hooks/{useVeiculoDaRota, usePreviaDeArquivo}.ts`; `services/{veiculoService, fotoService, apiCliente}.ts`; `types/veiculo.ts`; `utils/{formatos, datas}.ts` e `formatos.test.ts`; `styles/veiculos.css`; `tests/apiFalsa.tsx`. `README.md` (seção 11 e problemas comuns), `CLAUDE.md`, `docs/decisoes.md`, `docs/progresso.md`.
- Testes executados pelo Claude:
  - `.\.venv\Scripts\python.exe -m pytest` (backend): 247 passaram, 0 falharam (134 das etapas 1 e 2 + 113 novos). Incluem: dois usuários e um admin tentando ver e alterar veículo, leitura e foto de outro por ID direto; leitura e foto de outro veículo do MESMO dono; registro histórico que não reduz o km; agendada que não aumenta; transição isolada para realizada; correção de leitura com recálculo e rollback; placa por dono; inativação preservando histórico; upload com formato, conteúdo e tamanho inválidos; HEIC convertido; GPS removido; acesso indevido à foto; quatro trocas de capa simultâneas (5 rodadas); falha forçada no banco sem sobrar arquivo; limpeza de órfãos.
  - `npm test` (frontend): 68 passaram, 0 falharam; `npm run typecheck` sem erros; `npm run build` ok.
  - Fluxo real no Chrome (tela de celular 412×915, automatizado) com uvicorn + Vite ligados ao banco de TESTE e a uma pasta temporária de fotos: 17 passos, todos ok (conta, cadastro com capa, imagem carregada pelo endpoint protegido, atualizar km, corrigir leitura errada, leitura incoerente recusada, arquivo falso recusado, PNG enviado, troca de capa, apagar foto, segundo veículo, troca do veículo em uso, placa repetida, inativar, barra inferior, outra conta sem acesso ao veículo e à foto, sair). Log do backend sem erro 500 e sem senha ou token. As telas foram conferidas por capturas; um desalinhamento da placa no Início foi corrigido.
- Depende de validação da Paula:
  - Instalar as bibliotecas novas: `.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt` (pasta `backend`).
  - Rodar `gerenciar.py migrar` no banco de desenvolvimento (ele está na 0002; o `migrar` faz backup antes).
  - Testar as telas no navegador do computador com fotos de verdade (inclusive uma foto grande do celular).
  - Câmera do celular, HEIC vindo de um iPhone real e acesso pela rede local: etapa 10. O HEIC foi testado só com arquivo gerado por programa.
- Não coberto nesta etapa: listagem de todos os veículos para o admin (tela "Usuários e veículos", etapa 9; o acesso do admin por endereço direto já funciona e está testado); vínculo de foto com manutenção, diagnóstico e projeto e os filtros da galeria (etapas 4, 5 e 8); cartões de custo do "Meu veículo" e atalhos/alertas/indicadores do Início (etapas 4 a 9); miniaturas das fotos (a galeria carrega a imagem inteira, já reduzida a 2560 pontos).
- Validado pela Paula (30/09/2026): instalou as bibliotecas, aplicou a 0003 no banco de desenvolvimento, usou as telas (a pasta `backend\storage\veiculos` foi criada pelo envio de foto), fez o commit e enviou ao GitHub. Ela não relatou problemas nem detalhou cada teste. Observação: o commit da etapa 3 ficou com a mensagem "Etapa 2 completa" (`20dd5a8`); o conteúdo é o da etapa 3.
- Pendência de etapa anterior: envio real de e-mail por SMTP continua sem teste.
- Pendências para a próxima etapa (4 — manutenções e planos): entities `PlanoManutencao` e `Manutencao`; chaves compostas para garantir plano e manutenção do mesmo veículo; base fixa (`data_base`/`km_base`) nos planos no lugar do `CURRENT_DATE` e do zero inventado da view; faixas de 1.000 km/30 dias; pendentes sem alerta duplicado; `garantia_km` como limite absoluto; fotos ligadas a manutenção; os triggers de km da 0003 já tratam status e edição, faltam os testes pela API.

### Etapa 4 — Manutenções e planos (30/09/2026)
- Ficou funcionando (código + testes do Claude):
  - Migration 0004: base fixa dos planos (`data_base`/`km_base`), situação recalculada (`classificar_prazo`, faixas de 1.000 km/30 dias, "dados insuficientes" sem base), chaves compostas "mesmo veículo" para plano e fotos da manutenção.
  - Planos, manutenções realizadas/agendadas, aba Pendentes (cada obrigação uma vez), garantia com limite do hodômetro, lembrete da próxima, fotos ligadas à manutenção.
  - Migration 0005 (pedido da Paula): peças e mão de obra (`manutencao_item`), cada item com nome e valor; total = soma dos itens, garantido pelo banco (trigger + conferência adiada); sem itens, valor manual; manutenções antigas preservadas sem divisão inventada. Formulário com "+ Adicionar peça" / "+ Adicionar mão de obra", remover linha e prévia dos subtotais; popup "Ver valores" no detalhe e na aba Realizadas; agendada mostra valores estimados.
  - Espaçamento: `.cartao.lista-status` com espaço interno (data, quilometragem... não encostam mais na borda).
  - Proteção 503: com migration pendente, a API responde com a versão atual, a necessária e o comando `gerenciar.py migrar` (em vez de erro 500); `/api/saude` continua respondendo; aviso no terminal ao iniciar.
- Incidente corrigido: as telas de planos e pendentes davam erro 500 ("coluna s.intervalo_km não existe") porque o banco de desenvolvimento estava na 0003 com o código já esperando a 0004. A 0004 estava correta e não foi alterada; foi aplicada com `gerenciar.py migrar` (backup `meu_veiculo_20260930_181208_antes_de_migrar.dump`). A proteção 503 impede que isso volte a aparecer como erro 500.
- Arquivos criados/alterados: `backend/migrations/versions/{0004_manutencoes_e_planos, 0005_itens_da_manutencao}.py`; `backend/app/{main.py, dependencias.py}`; `backend/app/banco/versao.py`; `backend/app/entities/{manutencao, __init__}.py`; `backend/app/{repositories,services,controllers,routes,schemas}/manutencao_*.py`; `backend/app/services/erros.py`; `backend/app/controllers/erros_http.py`; `backend/app/routes/__init__.py`; `backend/tests/{test_manutencoes_api, test_manutencao_itens_api, test_migracao_0004, test_migracao_0005, test_banco_desatualizado, test_migracoes}.py`. `frontend/src/components/{ValoresManutencao, PecasManutencao}.tsx`; `pages/{Manutencao, ManutencaoForm, ManutencaoDetalhe, PlanoForm}Page.tsx` e `Manutencao.test.tsx`; `services/manutencaoService.ts`; `types/manutencao.ts`; `utils/formatos.ts` e `formatos.test.ts`; `styles/{manutencao, tema}.css`. `README.md` (seção 12 e problemas comuns), `docs/decisoes.md`, `docs/progresso.md`.
- Testes executados pelo Claude:
  - `.\.venv\Scripts\python.exe -m pytest` (backend, PostgreSQL de teste): 384 passaram, 0 falharam (inclui 12 da migration 0005 — banco vazio, banco já na 0004 preservando manutenções, desfazer/refazer, total diferente recusado pelo banco, centavos, itens inválidos, cascata —, 25 de peças e mão de obra pela API — criação, edição, remoção, subtotais, total, centavos, valor manual, total da tela recusado, agendada, isolamento entre usuários e veículos, admin, exclusão em cascata, veículo inativo — e 4 da proteção 503).
  - `npm test` (frontend): 103 passaram, 0 falharam; `npm run build` (com `tsc`) ok.
  - Fluxo real no Chrome (tela 412×915, automatizado) com uvicorn + Vite no banco de TESTE: 17 passos, todos ok (pendentes/planos sem 500, 5 itens adicionados um a um, remover linha, gravado 115,00 + 50,00 = 165,00, popup no detalhe, total "999.00" forçado direto na API recusado, edição, valor manual sem itens, popup na aba Realizadas, agendada estimada e concluída mantendo os itens, exclusão, outra conta com 404, espaçamento de 18px, aviso 503 com o banco na 0004 e volta ao normal depois do migrar). Log do backend sem erro 500, sem traceback e sem senha ou token. As capturas mostraram o botão "Ver valores" encostando no cartão; corrigido e conferido.
  - Banco de desenvolvimento: 0004 e 0005 aplicadas com backup (`..._181208_...` e `..._190715_...`); consultas de planos e pendentes do veículo 2 executadas sem erro; a manutenção existente (R$ 230,00) ficou igual e sem itens; o fluxo de teste não gravou nada nele.
- Depende de validação da Paula:
  - Reiniciar o backend e usar as telas com os dados reais: nova manutenção com peças e mão de obra, editar, "Ver valores" no detalhe e na aba Realizadas, agendada.
  - Conferir no terminal do PowerShell se o aviso de banco desatualizado aparece com acentos corretos (no log capturado pelo Claude os acentos saíram trocados por causa da codificação do arquivo de log; não foi possível ver o terminal dela).
  - Celular (Android/Chrome): etapa 10.
- Validado pela Paula (30/09/2026): testou as telas no computador dela e fez o commit (`61eb695`).
- Pendências para a próxima etapa (5 — diagnósticos): fotos ligadas a diagnóstico; manter o padrão "total calculado no backend" se diagnóstico tiver custo; envio real por SMTP continua sem teste.

### Etapa 5 — Diagnósticos (30/09/2026)
- Decisões da Paula (30/09/2026): apagar ou voltar para agendada a manutenção que resolveu → o diagnóstico é reaberto com aviso; manutenção agendada fica ligada como a prevista e resolve ao ser concluída; dá para resolver com uma manutenção nova ou com uma já registrada.
- Ficou funcionando (código + testes do Claude):
  - Migration 0006: chaves compostas "mesmo veículo" (diagnóstico → manutenção; foto → diagnóstico), trigger de coerência (resolvido só com realizada; aberto só com agendada; descartado sem manutenção), triggers na manutenção (concluir resolve, voltar para agendada reabre, data acompanha, apagar reabre) e conferência prévia que lista vínculos incompatíveis e para sem alterar nada.
  - Backend: `DiagnosticoService` (lista Abertos/Resolvidos/Todos paginada, detalhe, cadastro/edição com leitura do hodômetro, em observação, descartar com motivo, reabrir, apagar com fotos e arquivos, anotações, resolver com manutenção nova numa transação só, usar manutenção já registrada, aviso de garantia do mesmo sistema), 12 endpoints em `/api/veiculos/{id}/diagnosticos`; manutenção mostra os diagnósticos ligados e grava anotações automáticas; fotos aceitam `diagnostico_id` (um vínculo só, mesmo veículo) e o filtro `vinculo=diagnostico`.
  - Frontend: aba Diagnóstico (Abertos (n), Resolvidos, Todos, "Resolvidos recentemente"), "Novo diagnóstico" com sistema e gravidade em botões e orientação por gravidade, detalhe com selos, garantia, linha do tempo de anotações, fotos e ações; "Nova manutenção" com a faixa "Resolvendo o diagnóstico"; avisos no detalhe/edição/exclusão da manutenção; Início com problemas em aberto em "Precisa de atenção"; foto ligada a diagnóstico e filtro "Diagnósticos" na galeria.
  - Correção encontrada no teste: o diálogo de confirmação tirava o foco do campo de texto a cada letra (o espaço acionava "Cancelar"); agora o foco só muda ao abrir.
- Arquivos criados: `backend/migrations/versions/0006_diagnosticos.py`; `backend/app/entities/diagnostico.py`; `backend/app/{repositories/diagnostico_repository, services/diagnostico_service, schemas/diagnostico_schema, controllers/diagnostico_controller, routes/diagnostico_routes}.py`; `backend/tests/{test_migracao_0006, test_diagnosticos_api}.py`; `frontend/src/{types/diagnostico.ts, services/diagnosticoService.ts, components/PecasDiagnostico.tsx, pages/DiagnosticoPage.tsx, pages/DiagnosticoFormPage.tsx, pages/DiagnosticoDetalhePage.tsx, pages/Diagnostico.test.tsx, styles/diagnostico.css}`.
- Arquivos alterados: `backend/app/{dependencias.py, entities/__init__.py, routes/__init__.py, routes/veiculo_routes.py}`; `backend/app/repositories/{manutencao, foto}_repository.py`; `backend/app/services/{manutencao, foto}_service.py`; `backend/app/schemas/{manutencao, veiculo}_schema.py`; `backend/app/controllers/{manutencao, foto}_controller.py`; `backend/gerenciar.py`; `backend/tests/{test_migracoes, test_banco_desatualizado}.py`; `frontend/src/{App.tsx, main.tsx}`; `components/{BarraNavegacao, Formulario}.tsx`; `pages/{Inicio, ManutencaoForm, ManutencaoDetalhe, FotoNova, Fotos, FotoDetalhe}Page.tsx`; `pages/{Manutencao, Veiculos}.test.tsx`; `services/fotoService.ts`; `types/manutencao.ts`; `README.md` (seção 13 e problemas comuns), `docs/decisoes.md`, `docs/progresso.md`.
- Testes executados pelo Claude:
  - `.\.venv\Scripts\python.exe -m pytest` (backend, PostgreSQL de teste): 446 passaram, 0 falharam (384 das etapas anteriores + 62 novos: 15 da migration 0006 — banco vazio, banco na 0005 preservado, parada com vínculos incompatíveis sem alterar nada, desfazer/refazer, triggers, cascata — e 47 pela API — cadastro, validação, hodômetro, filtros e ordem, anotações, situações, resolução com manutenção nova, falha forçada desfazendo tudo, envio repetido e 3 envios simultâneos criando uma manutenção só, agendada prevista e concluída, reabrir por edição e exclusão, manutenção de outro veículo/usuário recusada, garantia, isolamento entre usuários e veículos do mesmo dono, admin, veículo inativo, fotos). Um teste antigo (`test_banco_desatualizado`) supunha que a última migration era a 0005; foi ajustado para calcular a lista.
  - `npm test` (frontend): 122 passaram, 0 falharam; `npm run build` (com `tsc`) ok.
  - Fluxo real no Chrome (tela 412×915, automatizado) com uvicorn + Vite no banco de TESTE: 16 passos, todos ok (banco vazio, cadastro, aviso de garantia, anotação, motivo digitado no diálogo, resolver com manutenção nova de R$ 280,00, envio repetido 409, apagar manutenção reabre, agendada prevista e concluída, Início, lista, foto ligada, outra conta com 404, sem 5xx e sem erro no console). Capturas conferidas com o PDF; dois espaçamentos ajustados.
  - Banco de desenvolvimento: `gerenciar.py migrar` aplicou a 0006 com backup `meu_veiculo_20260930_203657_antes_de_migrar.dump`; conferência somente leitura: versão 0006, chaves e triggers criados, dados preservados (1 usuário, 2 veículos, 2 manutenções com 9 itens, 2 planos, 2 fotos, 0 diagnósticos). O fluxo de teste não gravou nada nele.
- Depende de validação da Paula:
  - Reiniciar o backend e usar as telas com os dados reais: registrar um problema, anotar, resolver com manutenção nova (realizada e agendada), usar uma já registrada, descartar, reabrir, foto ligada ao diagnóstico.
  - Celular (Android/Chrome): etapa 10.
- Pendências para a próxima etapa (6 — gastos e finanças): envio real por SMTP continua sem teste; diagnóstico não entra nas despesas (o custo é o da manutenção).
