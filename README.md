# Meu Veículo

Aplicação para cada usuário acompanhar seus veículos, gastos, abastecimentos,
manutenções, diagnósticos, projetos de melhoria e fotos. É uma aplicação web
responsiva e instalável (PWA), feita com React + TypeScript no frontend,
FastAPI (Python) no backend e PostgreSQL no banco de dados.

> **Estado atual: etapa 1 (estrutura do projeto).** Existe a base do backend
> em camadas, as migrations do banco e uma tela "Situação do sistema". As
> funcionalidades do aplicativo (login, veículos, manutenções...) entram nas
> próximas etapas. Veja `docs/progresso.md`.

---

## Sumário

1. [Programas necessários](#1-programas-necessários)
2. [Estrutura de pastas](#2-estrutura-de-pastas)
3. [Arquitetura](#3-arquitetura)
4. [Primeira configuração (uma vez só)](#4-primeira-configuração-uma-vez-só)
5. [Banco de dados: instalação, atualização e backup](#5-banco-de-dados-instalação-atualização-e-backup)
6. [Iniciar o sistema no dia a dia](#6-iniciar-o-sistema-no-dia-a-dia)
7. [Rodar os testes](#7-rodar-os-testes)
8. [Problemas comuns](#8-problemas-comuns)

---

## 1. Programas necessários

| Programa | Versão usada no projeto | Para que serve |
|---|---|---|
| Python | 3.13 | roda o backend |
| Node.js | 24 (com npm 10) | roda o frontend |
| PostgreSQL | 16 (mínimo 15) | banco de dados |
| Git | 2.44 | histórico do projeto |
| VS Code | atual | editor |

O PostgreSQL precisa ser 15 ou mais novo: as próximas migrations usam
`ON DELETE SET NULL (coluna)`, que só existe a partir da versão 15.

## 2. Estrutura de pastas

```
meu-veiculo/
├── README.md                    este guia
├── CLAUDE.md                    instruções do projeto para o Claude Code
├── database/original/           SQL recebido (somente leitura, nunca editar)
├── docs/                        requisitos, telas, progresso e decisões
├── backend/
│   ├── .env.example             modelo de configuração (sem senhas)
│   ├── requirements.txt         dependências (versões travadas)
│   ├── requirements-dev.txt     dependências de teste
│   ├── gerenciar.py             comandos do banco (criar, migrar, backup...)
│   ├── alembic.ini              configuração das migrations
│   ├── migrations/versions/     migrations numeradas (0001, 0002...)
│   ├── tests/                   testes (pytest, PostgreSQL de teste)
│   └── app/
│       ├── main.py              cria a API e registra as routes
│       ├── config.py            lê o backend/.env
│       ├── dependencias.py      monta repository → service → controller
│       ├── routes/              endereços da API
│       ├── controllers/         recebem a requisição e montam a resposta HTTP
│       ├── services/            regras de negócio
│       ├── repositories/        acesso ao PostgreSQL
│       ├── entities/            o que o sistema representa (tabelas mapeadas)
│       ├── schemas/             formato JSON de entrada e saída
│       └── banco/               conexão, sessão, migrations e backup
└── frontend/
    ├── package.json             dependências (versões exatas) e scripts
    ├── package-lock.json        trava de todas as versões
    ├── vite.config.ts           servidor de desenvolvimento e proxy /api
    └── src/
        ├── main.tsx, App.tsx    ponto de partida
        ├── pages/               telas inteiras (uma por endereço)
        ├── components/          peças reaproveitáveis (cabeçalho, selo...)
        ├── services/            chamadas à API
        ├── types/               formatos de dados (TypeScript)
        ├── utils/               funções auxiliares (datas, dinheiro...)
        ├── styles/              tema visual (cores do PDF)
        └── tests/               configuração dos testes
```

## 3. Arquitetura

### 3.1 As três partes

- **Frontend (React)**: as telas. Roda no navegador do computador ou do celular.
- **API (FastAPI)**: recebe os pedidos das telas, confere permissões, aplica as regras e fala com o banco.
- **Banco (PostgreSQL)**: guarda os dados. **Só o backend acessa o banco.** O celular nunca recebe endereço, usuário ou senha do PostgreSQL.

Em desenvolvimento, o frontend chama sempre `/api/...` no próprio endereço
dele, e o Vite repassa a chamada para o backend (proxy, configurado em
`frontend/vite.config.ts`). Assim o navegador só precisa conhecer um endereço.

### 3.2 Backend em camadas: Route → Controller → Service → Repository

Cada requisição passa pelas camadas nesta ordem, e cada camada só conversa
com a de baixo:

```
Navegador ──HTTP──▶ Route ──▶ Controller ──▶ Service ──▶ Repository ──▶ banco/ ──▶ PostgreSQL
                                   ▲             │             │
                                schemas       entities      entities
```

| Camada | Pasta | Responsabilidade | Não pode |
|---|---|---|---|
| **Route** | `app/routes/` | Define o endereço (`GET /api/saude`), o método e o formato da resposta. Entrega a requisição ao controller. | ter regra, acessar service, repository ou banco |
| **Controller** | `app/controllers/` | Recebe e organiza a requisição, chama o service e transforma o resultado em resposta HTTP (código 200, 404, 503...). Traduz erros de negócio em códigos HTTP (`erros_http.py`). | escrever SQL, acessar repository ou banco |
| **Service** | `app/services/` | Regras de negócio: o que pode, o que não pode, cálculos, quando começa e termina uma transação. | conhecer HTTP (FastAPI) ou SQL (SQLAlchemy) |
| **Repository** | `app/repositories/` | Todo o acesso ao PostgreSQL: consultas e gravações. Converte erros técnicos em erros simples (`BancoIndisponivel`). | conhecer HTTP ou regras de negócio |
| **Entity** | `app/entities/` | O que o sistema representa. Tabelas viram classes do SQLAlchemy (a partir da etapa 2). Objetos calculados, como a situação do sistema, são dataclasses. | depender das outras camadas |
| **Schema** | `app/schemas/` | Formato JSON que a API recebe e devolve (Pydantic). Um schema de resposta nunca inclui campos internos, como `senha_hash`. | acessar banco ou regras |
| **Banco** | `app/banco/` | Conexão (sempre no fuso `America/Sao_Paulo`), sessão e transação, migrations, backup e o SQL original. | depender das camadas acima |

`app/dependencias.py` monta as peças para cada requisição
(sessão → repository → service → controller). `app/main.py` só cria a API e
registra as routes.

**Essas regras são verificadas por teste.** `tests/test_arquitetura.py` lê os
`import` de cada arquivo e falha se, por exemplo, um service importar FastAPI
ou uma route importar um repository.

### 3.3 Exemplo real: `GET /api/saude`

| Passo | Arquivo | O que acontece |
|---|---|---|
| 1 | `routes/saude_routes.py` | Recebe `GET /api/saude` e pede o controller pronto a `dependencias.py`. |
| 2 | `controllers/saude_controller.py` | Chama `service.verificar()`. Responde 200 se o banco respondeu, 503 se não. |
| 3 | `services/saude_service.py` | Regra: banco em dia, com migration pendente, sem controle ou fora do ar. Escolhe a mensagem. |
| 4 | `repositories/saude_repository.py` | Pergunta ao PostgreSQL a data de hoje, o fuso e a versão das migrations. |
| 5 | `banco/conexao.py`, `banco/migracoes.py` | Abrem a conexão e leem a tabela de controle do Alembic. |

Se o PostgreSQL estiver desligado: o repository captura o erro técnico e
levanta `BancoIndisponivel`, sem host, usuário nem detalhes; o service monta a
situação "banco indisponível"; o controller responde 503.

### 3.4 Transações

Cada requisição recebe uma sessão do banco. O **service** decide o que precisa
ser gravado junto, usando `UnidadeDeTrabalho.transacao()` (`banco/sessao.py`).
Se qualquer parte falhar, nada é gravado. Exemplo que virá na etapa 5:

```python
with self.uow.transacao():
    manutencao = self.manutencoes.criar(dados)
    self.diagnosticos.resolver(diagnostico_id, manutencao.id)
```

### 3.5 Como acrescentar um endpoint (roteiro para as próximas etapas)

Exemplo: listar os veículos do usuário (etapa 3).

1. **Migration** (se precisar mudar o banco): `migrations/versions/000N_descricao.py`. Nunca edite uma migration já aplicada.
2. **Entity**: `entities/veiculo.py` com a classe `Veiculo(Base)` mapeando a tabela existente. O `tests/test_entities.py` confere se ela bate com o banco.
3. **Repository**: `repositories/veiculo_repository.py`, com métodos como `listar_do_usuario(usuario_id)`.
4. **Service**: `services/veiculo_service.py`, com as regras (quem pode ver o quê, normalização da placa...). Erros de regra usam as classes de `services/erros.py` (`NaoEncontrado`, `AcessoNegado`, `Conflito`...).
5. **Schemas**: `schemas/veiculo_schema.py`, com os formatos de entrada e saída.
6. **Controller**: `controllers/veiculo_controller.py`.
7. **Route**: `routes/veiculo_routes.py`, incluída em `routes/__init__.py`.
8. **Dependências**: em `dependencias.py`, uma função que monta o controller.
9. **Testes**: service com repository falso, repository no banco de teste e endpoint de ponta a ponta.

### 3.6 Frontend

O frontend segue a organização comum de projetos React (não a do backend):

| Pasta | O que vai nela |
|---|---|
| `pages/` | uma tela inteira por endereço (ex.: `SituacaoSistemaPage.tsx`; depois `LoginPage.tsx`, `InicioPage.tsx`...) |
| `components/` | peças visuais reaproveitáveis (`CabecalhoMarca`, `SeloStatus`; depois botões, cartões, barra de navegação) |
| `services/` | conversa com a API. `apiCliente.ts` é o único lugar que chama `fetch`. |
| `types/` | formatos dos dados, iguais aos schemas do backend |
| `utils/` | funções auxiliares. `datas.ts` formata datas **sem** `new Date()`, para não voltar um dia por causa do fuso. |
| `styles/` | tema com as cores do PDF (verde-petróleo, fundo claro, cartões) |

As fontes (Barlow e Barlow Condensed) vêm dentro do projeto (`@fontsource`),
sem depender do Google Fonts.

## 4. Primeira configuração (uma vez só)

Todos os comandos são para o **PowerShell** (terminal do VS Code). A pasta de
cada comando está indicada. Se usar o **CMD** (prompt `C:\>`), os comandos são
os mesmos, trocando `.\.venv\Scripts\python.exe` por `.venv\Scripts\python.exe`.

### 4.1 Permitir o npm no PowerShell

O Windows bloqueia scripts no PowerShell por padrão, e o `npm` é um script.
Rode uma vez (em qualquer pasta):

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Isso vale só para o seu usuário e permite scripts criados no seu computador.
Alternativa sem mudar nada: use `npm.cmd` no lugar de `npm` nos comandos abaixo.

### 4.2 Backend: ambiente virtual e dependências

Pasta `meu-veiculo\backend`:

```powershell
cd C:\Users\j0n4s\OneDrive\Documentos\meu-veiculo\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

O ambiente virtual (`.venv`) guarda as bibliotecas só deste projeto. Neste
guia, o Python do ambiente é chamado direto (`.\.venv\Scripts\python.exe`),
sem precisar "ativar" nada.

### 4.3 Backend: arquivo `.env`

Pasta `meu-veiculo\backend`:

```powershell
Copy-Item .env.example .env
```

Abra `backend\.env` no VS Code e preencha `DB_SENHA` com uma senha **nova**,
só da aplicação (não use a do `postgres`). O `.env` não vai para o Git.

### 4.4 Criar o usuário da aplicação e os bancos

Pasta `meu-veiculo\backend`:

```powershell
.\.venv\Scripts\python.exe gerenciar.py criar-bancos
```

O comando pede a senha do usuário `postgres` (a da instalação do PostgreSQL).
Ela não aparece ao digitar e não fica gravada. Resultado esperado:

```
Usuário 'meu_veiculo_app' criado (sem poderes de administrador).
Banco 'meu_veiculo' criado.
Banco 'meu_veiculo_teste' criado.
```

O que ele faz:

- cria o usuário `meu_veiculo_app`, sem poderes de administrador do servidor;
- cria `meu_veiculo` (desenvolvimento) e `meu_veiculo_teste` (testes);
- define o fuso `America/Sao_Paulo` nos dois bancos.

Se rodar de novo, não apaga nada: só atualiza a senha do usuário para a do `.env`.

### 4.5 Frontend: dependências

Pasta `meu-veiculo\frontend`:

```powershell
cd C:\Users\j0n4s\OneDrive\Documentos\meu-veiculo\frontend
npm ci
```

`npm ci` instala exatamente as versões do `package-lock.json`.

## 5. Banco de dados: instalação, atualização e backup

Os comandos desta seção são rodados na pasta `meu-veiculo\backend`.
Acrescente `--teste` para agir no banco de teste.

### 5.1 Ver o estado

```powershell
.\.venv\Scripts\python.exe gerenciar.py estado
```

Mostra a situação do banco, a versão aplicada e as migrations pendentes.

### 5.2 Banco vazio (instalação nova)

```powershell
.\.venv\Scripts\python.exe gerenciar.py migrar
```

Aplica a 0001, que é o SQL original **sem alterações**, e depois as
seguintes. Antes de rodar, a 0001 confere a "impressão digital" (SHA-256) de
`database/original/meu_veiculo_banco.sql`. Se o arquivo tiver sido editado,
ela se recusa a rodar.

### 5.3 Banco que já existe (criado com o SQL original, por exemplo no pgAdmin)

**Nunca rode o SQL original de novo nesse banco.** Faça:

```powershell
.\.venv\Scripts\python.exe gerenciar.py backup
.\.venv\Scripts\python.exe gerenciar.py adotar-banco-existente
.\.venv\Scripts\python.exe gerenciar.py migrar
```

O `adotar-banco-existente` recria o SQL original num esquema temporário,
compara tabelas, colunas, restrições, índices, views, triggers, funções e
domains com o seu banco, e desfaz o esquema temporário. Se tudo for igual, ele
só registra a 0001 como aplicada. Se houver diferença, ele lista cada uma e
**não altera nada**.

### 5.4 Backup e recuperação

- `migrar` faz backup automático antes de atualizar um banco que já tem migrations aplicadas.
- Backup manual: `.\.venv\Scripts\python.exe gerenciar.py backup`.
- Os arquivos ficam em `backend\backups\` (fora do Git, porque contêm dados).
- Cada migration roda na própria transação: se uma falhar, só ela é desfeita, e as anteriores continuam aplicadas.

Para restaurar um backup (emergência: apaga o conteúdo atual do banco e põe o do arquivo):

```powershell
& "C:\Program Files\PostgreSQL\16\bin\pg_restore.exe" --clean --if-exists --no-owner -h localhost -U meu_veiculo_app -d meu_veiculo backend\backups\NOME_DO_ARQUIVO.dump
```

(Rode na pasta `meu-veiculo`. O comando pede a senha do `DB_SENHA`.)

## 6. Iniciar o sistema no dia a dia

São dois terminais abertos ao mesmo tempo.

**Terminal 1, backend** (pasta `meu-veiculo\backend`):

```powershell
cd C:\Users\j0n4s\OneDrive\Documentos\meu-veiculo\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Esperado: `Uvicorn running on http://127.0.0.1:8000`. A documentação
automática da API fica em http://127.0.0.1:8000/docs.

**Terminal 2, frontend** (pasta `meu-veiculo\frontend`):

```powershell
cd C:\Users\j0n4s\OneDrive\Documentos\meu-veiculo\frontend
npm run dev
```

Esperado: `Local: http://localhost:5173/`. Abra esse endereço no navegador. A
tela "Situação do sistema" deve mostrar API "No ar", Banco "Conectado",
Migrations "Em dia (versão 0001)", o fuso e a data de hoje.

Para parar: `Ctrl + C` em cada terminal.

O acesso pelo celular (rede local, IP do computador, firewall e HTTPS) será
configurado e documentado na etapa 10. No celular, `localhost` é o próprio
celular, não o seu computador.

## 7. Rodar os testes

**Backend** (pasta `meu-veiculo\backend`), com PostgreSQL real no banco de teste:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Os testes **apagam e recriam** o banco de teste (`DB_NOME_TESTE`). Por
segurança, eles se recusam a rodar se esse nome não terminar em `_teste` ou for
igual ao banco de desenvolvimento.

**Frontend** (pasta `meu-veiculo\frontend`):

```powershell
npm test
npm run typecheck
```

## 8. Problemas comuns

| Mensagem | Causa provável | O que fazer |
|---|---|---|
| `npm : O arquivo ... não pode ser carregado porque a execução de scripts foi desabilitada` | bloqueio de scripts do PowerShell | seção 4.1, ou use `npm.cmd` |
| `Não consegui conectar ao banco de teste` (pytest) | PostgreSQL parado, `.env` sem senha ou bancos não criados | confira o serviço `postgresql-x64-16` em Serviços do Windows; seção 4.3 e 4.4 |
| `Não consegui entrar como 'postgres'` | senha errada do administrador | é a senha definida na instalação do PostgreSQL |
| `Este banco já tem tabelas, mas não tem registro de migrations` | banco criado fora do controle de migrations | seção 5.3 |
| `O arquivo ... meu_veiculo_banco.sql foi alterado` | alguém editou o SQL original | `git checkout -- database/original/meu_veiculo_banco.sql` |
| Tela mostra API "Sem resposta" | backend não está rodando | Terminal 1 da seção 6 |
| `EPERM`, arquivos travados ou lentidão no `npm` | a pasta está dentro do OneDrive, que sincroniza `node_modules` e `.venv` | pause a sincronização do OneDrive enquanto trabalha ou mova o projeto para `C:\projetos\meu-veiculo` |
