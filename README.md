# Meu Veículo

Aplicação para cada usuário acompanhar seus veículos, gastos, abastecimentos,
manutenções, diagnósticos, projetos de melhoria e fotos. É uma aplicação web
responsiva e instalável (PWA), feita com React + TypeScript no frontend,
FastAPI (Python) no backend e PostgreSQL no banco de dados.

> **Estado atual: etapa 3 (veículos, quilometragem e base das fotos).** Já
> funcionam: contas e permissões (etapa 2), cadastro e edição de veículos,
> veículo em uso, inativação, leituras de quilometragem com histórico e
> correção, fotos com capa e galeria, e a barra de navegação inferior.
> Manutenções, diagnósticos, finanças e o restante entram nas próximas etapas.
> Veja `docs/progresso.md`.

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
9. [Contas, senhas e permissões](#9-contas-senhas-e-permissões)
10. [E-mail (recuperação de senha)](#10-e-mail-recuperação-de-senha)
11. [Veículos, quilometragem e fotos](#11-veículos-quilometragem-e-fotos)

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
│   ├── storage/                 arquivos das fotos (fora do Git; criada no primeiro envio)
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
        ├── main.tsx, App.tsx    ponto de partida e endereços (rotas) das telas
        ├── pages/               telas inteiras (uma por endereço)
        ├── components/          peças reaproveitáveis (campos, botões, cabeçalho...)
        ├── contexts/            dados compartilhados entre telas (usuário logado)
        ├── hooks/               lógica reaproveitável (envio de formulário)
        ├── services/            chamadas à API
        ├── types/               formatos de dados (TypeScript)
        ├── utils/               funções auxiliares (datas, validação...)
        ├── styles/              tema visual (cores do PDF)
        └── tests/               configuração e apoio dos testes
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
| `pages/` | uma tela inteira por endereço (`LoginPage`, `CadastroPage`, `InicioPage`, `MaisPage`, `VeiculosPage`, `VeiculoFormPage`, `VeiculoDetalhePage`, `QuilometragemPage`, `FotosPage`, `FotoNovaPage`, `FotoDetalhePage`, `ContaPage`...) |
| `components/` | peças visuais reaproveitáveis (`CampoTexto`, `CampoSenha` com o olho, `BotaoEnviar`, `Alerta`, `TopoComVoltar`, `RotaProtegida`, `BarraNavegacao`, `Formulario` com opções/chave/diálogo de confirmação, `PecasVeiculo` com placa/hodômetro/foto...) |
| `contexts/` | `AuthContext`: quem está logado. `VeiculosContext`: os veículos da conta e o veículo em uso. Ficam só na memória da página (nada em `localStorage`). |
| `hooks/` | `useEnvioFormulario`: "enviando", trava contra envio duplicado e erros da API por campo. `useVeiculoDaRota`: carrega o veículo do endereço. |
| `services/` | conversa com a API. `apiCliente.ts` é o único lugar que chama `fetch` e envia o cabeçalho `X-MV-Requisicao`. |
| `types/` | formatos dos dados, iguais aos schemas do backend |
| `utils/` | funções auxiliares. `datas.ts` formata datas **sem** `new Date()`, para não voltar um dia por causa do fuso. `formatos.ts` trata km, placa e dinheiro (dinheiro sempre como texto, nunca ponto flutuante). |
| `styles/` | `tema.css` com as cores do PDF (verde-petróleo, fundo claro, cartões) e `veiculos.css` com a barra inferior e as telas de veículo |

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

Esperado: `Local: http://localhost:5173/`. Abra esse endereço no navegador: a
tela "Entrar" aparece. Crie uma conta em "Criar conta" e você vai para o
Início. A tela http://localhost:5173/situacao mostra API "No ar", Banco
"Conectado", Migrations "Em dia" com a versão mais recente, o fuso e a data.

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
| `A migration 0002 parou: há e-mails incompatíveis` | dois cadastros antigos com o mesmo e-mail, diferentes só em maiúsculas ou espaços, ou e-mail sem `@` | seção 9.5 |
| `Muitas tentativas de entrada` (tela Entrar) | 5 senhas erradas para o mesmo e-mail em 15 minutos | espere 15 minutos ou use "Esqueci minha senha" |
| `Requisição recusada: ela não veio do aplicativo` | chamada à API sem o cabeçalho do app (ex.: pelo `/docs`) | normal para gravações fora do app; use as telas |
| Tela Situação: "Pendente: 0002" (ou 0003) | o banco de desenvolvimento ainda não recebeu a migration nova | `.\.venv\Scripts\python.exe gerenciar.py migrar` (pasta `backend`) |
| `relação "leitura_km" não existe` ou erro 500 ao abrir o Início | mesma causa: falta aplicar a migration 0003 | `.\.venv\Scripts\python.exe gerenciar.py migrar` (pasta `backend`) |
| `ModuleNotFoundError: No module named 'PIL'` (ou `pillow_heif`, `multipart`) ao iniciar o backend | as bibliotecas novas da etapa 3 não foram instaladas | `.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt` (pasta `backend`) |
| `A migration 0003 parou: há placas incompatíveis` | dois veículos da mesma conta ficariam com a mesma placa, ou placa com caractere inválido | seção 11.6 |
| `Esta leitura não combina com o histórico` | a quilometragem informada contradiz outra leitura (dia anterior com km maior, ou dia posterior com km menor) | confira valor e data; se a leitura antiga é que está errada, use "Corrigir" no histórico (seção 11.2) |
| `Envio grande demais` ou `Foto grande demais` | foto acima de 10 MB | reduza a resolução na câmera ou escolha outra foto |
| Foto aparece como "Imagem indisponível" | o arquivo sumiu da pasta `backend\storage` | seção 11.5 |
| Tela mostra `O banco de dados está na versão 0004 e o sistema precisa da 0005...` (HTTP 503) | o código foi atualizado com uma migration nova e o banco ainda não | `.\.venv\Scripts\python.exe gerenciar.py migrar` (pasta `backend`); não precisa reiniciar o backend (seção 12.5) |
| `coluna ... não existe` (erro 500) no terminal do backend | mesma causa, em versão antiga do código sem o aviso 503 | `.\.venv\Scripts\python.exe gerenciar.py migrar` (pasta `backend`) |
| Ao salvar a manutenção aparece "A data não pode ser anterior" | ela resolve um diagnóstico identificado depois dessa data | corrija a data da manutenção ou a do diagnóstico (seção 13.3) |
| `gerenciar.py migrar` para na 0006 com uma lista de diagnósticos ou fotos | vínculos antigos entre veículos diferentes ou incoerentes | corrija os vínculos listados (seção 13.6); nada foi alterado |
| `gerenciar.py migrar` para na 0007 com uma lista de gastos pendentes | gastos antigos pendentes sem vencimento | informe o vencimento ou marque como pago (seção 14.6); nada foi alterado |
| `gerenciar.py migrar` para na 0008 com uma lista de abastecimentos | total gravado muito diferente de litros × preço | corrija litros, preço ou total (seção 15.6); nada foi alterado |
| `Com peças ou mão de obra detalhadas, o total é calculado automaticamente` | foi enviado um total junto com itens | normal: com itens, o total é a soma; tire os itens para informar só o total (seção 12.3) |
| `A migration 0004 parou: ... está ligada ao plano ..., que é do veículo ...` | registro antigo ligado a plano ou manutenção de outro veículo | seção 12.6 |

## 9. Contas, senhas e permissões

### 9.1 Como funciona

| Item | Regra |
|---|---|
| Cadastro | nome, e-mail, senha e confirmação. A conta nasce com perfil **padrão**. Um campo a mais (como `"perfil": "admin"`) faz o pedido ser recusado. |
| E-mail | guardado sem espaços nas pontas e em minúsculas: ` Paula@Email.com ` e `paula@email.com` são o mesmo. O banco recusa outra grafia (restrição da migration 0002). |
| Senha | de 8 a 128 caracteres, qualquer caractere; não pode ser só espaços, igual ao e-mail ou uma das senhas mais usadas ("12345678", "senha123"...). Não exigimos maiúscula e símbolo: isso leva a senhas previsíveis como "Senha@123". Frases longas são mais fortes. |
| Hash | **Argon2id** (RFC 9106, recomendado pela OWASP): 3 passadas, 64 MiB de memória, 4 linhas; sal aleatório por senha. A senha nunca é gravada nem devolvida. |
| Sessão | ao entrar, o navegador recebe um cookie `HttpOnly` (o JavaScript não lê), `SameSite=Lax` e restrito a `/api`. O banco guarda só o SHA-256 do token. Dura 30 dias (`SESSAO_DIAS`). |
| Sair | encerra a sessão deste aparelho no banco; o token deixa de valer mesmo que alguém o tenha copiado. |
| Trocar senha | exige a senha atual; os outros aparelhos saem, este continua. |
| Conta desativada | perde o acesso na próxima ação, mesmo com uma sessão aberta antes. |
| Limite de tentativas | login: 5 erros por e-mail ou 20 por endereço de rede em 15 minutos. Recuperação: 3 pedidos por e-mail por hora (sem avisar, para não revelar a conta) ou 10 por endereço de rede (aviso "Muitos pedidos"). |
| Requisições forjadas | toda gravação exige o cabeçalho `X-MV-Requisicao: 1`, que só o app envia. Outro site não consegue acrescentar esse cabeçalho. |

### 9.2 Recuperação de senha

1. Em "Esqueci minha senha", a pessoa informa o e-mail. A resposta é **sempre a mesma**, exista ou não a conta.
2. Se a conta existe e está ativa, o sistema envia um link `http://localhost:5173/redefinir-senha#token=...`, válido por 60 minutos (`RECUPERACAO_MINUTOS`) e de **uso único**. Um link novo invalida os anteriores.
3. O banco guarda só o hash do token. A parte depois do `#` não é enviada a nenhum servidor, e a tela a apaga do endereço assim que abre.
4. Ao salvar a senha nova, o link é consumido e a senha trocada **na mesma transação**. Se dois pedidos chegarem juntos com o mesmo link, o banco faz um esperar o outro, e só o primeiro funciona (há teste automático disso).
5. Depois da troca, **todas** as sessões da conta são encerradas, inclusive a do aparelho usado.

### 9.3 Permissões no backend

- As routes usam `SessaoAtualDep` (exige estar logado; senão 401) ou `AdminDep` (exige perfil admin; senão 403), de `app/dependencias.py`.
- Esconder um botão na tela não protege nada: a verificação é sempre no backend.
- Nas próximas etapas, cada service também confere a quem pertence cada veículo e registro, sem confiar em IDs enviados pela tela.

### 9.4 Primeiro administrador

Não existe senha fixa nem endereço da API para virar admin. O primeiro admin é
criado assim:

1. Crie a conta normalmente pela tela "Criar conta".
2. Na pasta `meu-veiculo\backend`, rode:

   ```powershell
   .\.venv\Scripts\python.exe gerenciar.py promover-admin paula@email.com
   ```

   Resultado esperado: `A conta paula@email.com agora é administradora.`
3. Saia e entre de novo (ou recarregue a página) para ver o perfil "Admin".

Só quem tem a senha do banco (`backend\.env`) consegue rodar esse comando.

O banco **não deixa ficar sem administrador ativo**: desativar, rebaixar ou
apagar o último admin ativo é recusado por um trigger, inclusive quando duas
pessoas tentam ao mesmo tempo.

### 9.5 Se a migration 0002 parar por causa de e-mails antigos

Ela lista, por exemplo: `ficariam iguais a 'ana@email.com': usuários 3 (ana@email.com), 7 ( Ana@email.com)`.
Nada foi alterado. Decida qual cadastro manter e corrija o outro à mão, por
exemplo no pgAdmin, trocando o e-mail do cadastro duplicado por um endereço
diferente e verdadeiro. Não apague nem una contas sem conferir os veículos de
cada uma. Depois rode de novo `gerenciar.py migrar`.

## 10. E-mail (recuperação de senha)

### 10.1 Desenvolvimento: modo "arquivo" (padrão, gratuito)

Com `EMAIL_MODO=arquivo` (padrão), nenhum e-mail sai do computador: cada
mensagem vira um arquivo `.eml` em `backend\emails_dev\`.

Para testar:

1. Em http://localhost:5173/esqueci-senha, informe o e-mail de uma conta.
2. Abra a pasta `backend\emails_dev\` e o arquivo `.eml` mais recente, com o Outlook, o Thunderbird ou o VS Code.
3. Copie o link inteiro (começa com `http://localhost:5173/redefinir-senha#token=`) e cole no navegador.

A pasta `emails_dev` não vai para o Git: os arquivos contêm links válidos.

### 10.2 Envio real: modo "smtp"

No `backend\.env`:

```
EMAIL_MODO=smtp
EMAIL_REMETENTE=Meu Veículo <seu-endereco@provedor.com>
SMTP_HOST=smtp.provedor.com
SMTP_PORTA=587
SMTP_SEGURANCA=starttls
SMTP_USUARIO=seu-endereco@provedor.com
SMTP_SENHA=senha-de-app-do-provedor
URL_FRONTEND=http://localhost:5173
```

- Gmail e Outlook exigem uma "senha de app" (criada nas configurações de segurança da conta), não a senha normal.
- Porta 587 usa `starttls`; porta 465 usa `ssl`.
- `URL_FRONTEND` precisa ser o endereço que a pessoa abre no navegador (no celular, será o IP do computador; etapa 10).
- Reinicie o backend depois de mudar o `.env`.
- Uma falha de envio aparece no terminal do backend só como `Falha ao enviar e-mail (tipo do erro)`, sem destinatário nem conteúdo. A tela mostra a mesma mensagem de sempre.

**Situação de teste:** o envio real por SMTP tem código pronto, mas **não foi
testado** com um provedor de verdade: depende da sua conta de e-mail. O modo
"arquivo" foi testado de ponta a ponta.

Alternativa local que imita um servidor SMTP: o programa gratuito **Mailpit**
(https://mailpit.axllent.org). Com ele rodando, use `EMAIL_MODO=smtp`,
`SMTP_HOST=localhost`, `SMTP_PORTA=1025`, `SMTP_SEGURANCA=nenhuma`, sem
usuário e senha, e veja as mensagens em http://localhost:8025.

## 11. Veículos, quilometragem e fotos

### 11.1 Veículos

| Item | Regra |
|---|---|
| Dono | sempre quem está logado. O cadastro recusa `usuario_id` vindo da tela. |
| Placa | guardada em maiúsculas, sem hífen e sem espaços (`abc-1234` vira `ABC1234`). Aceita o formato antigo (`ABC-1234`) e o Mercosul (`ABC1D23`). A tela mostra o hífen só na placa antiga. |
| Placa repetida | a unicidade é **por conta**: a mesma pessoa não cadastra a placa duas vezes, mas duas pessoas podem ter a mesma placa (compra e venda entre usuários). |
| Combustível | os sete valores do banco: flex, gasolina, etanol, diesel, GNV, híbrido e elétrico. |
| Dinheiro | o valor pago viaja como texto (`"65000.00"`) e é `Decimal` no backend. Mais de duas casas decimais é recusado, não arredondado em silêncio. |
| Veículo em uso | fica gravado na conta (vale em qualquer aparelho). O veículo recém-cadastrado vira o veículo em uso. |
| Inativar | para carro vendido. Nada é apagado: leituras, fotos e registros continuam consultáveis. O veículo inativo fica somente para leitura até ser reativado. Não existe "apagar veículo". |
| Permissão | quem não é o dono (nem admin) recebe "Veículo não encontrado", a mesma resposta de um veículo que não existe. |

### 11.2 Quilometragem

Cada atualização é uma **leitura**: o valor e o dia em que o hodômetro marcava
esse valor. A tabela `leitura_km` guarda também quando a leitura foi digitada.

- A quilometragem atual é sempre a **maior leitura válida**, e a data mostrada
  na tela é a data dessa leitura. Quem calcula é o banco, a cada mudança.
- Registro antigo (km menor) entra no histórico e **não reduz** a quilometragem atual.
- Manutenção apenas agendada não gera leitura. Mudar só o status para
  "realizada" gera (o trigger do SQL original não via essa mudança).
- O hodômetro só anda para a frente: uma leitura de um dia anterior com km
  maior, ou de um dia posterior com km menor, é recusada. No mesmo dia,
  qualquer ordem é aceita.
- Veículos que já existiam antes da migration 0003 podem ter uma leitura
  "anterior ao histórico", sem data. A tela mostra "Data da leitura
  desconhecida" em vez de inventar uma data.

**Corrigir uma quilometragem digitada errada** (tela Quilometragem, botão
"Corrigir" na leitura):

1. Informe o valor certo e, se quiser, o motivo.
2. A leitura errada fica no histórico, riscada e marcada como "Anulada"; a
   leitura nova entra com a mesma data.
3. O banco recalcula a quilometragem atual na hora. Os indicadores das
   próximas etapas (consumo, custo por km, planos) são sempre calculados a
   partir das leituras válidas, então refletem a correção.

"Anular" retira uma leitura que não deveria existir (não é possível anular a
única leitura do veículo). Leituras que vieram de um abastecimento, manutenção
ou diagnóstico são corrigidas editando esse registro.

### 11.3 Fotos

| Item | Regra |
|---|---|
| Formatos | JPEG, PNG, WebP e HEIC, até 10 MB (10.485.760 bytes). |
| Conferência | o backend identifica o formato pelos primeiros bytes do arquivo e abre a imagem inteira. A extensão e o tipo informado pelo navegador não são levados em conta. |
| Regravação | a imagem é regravada do zero: somem conteúdos escondidos e os metadados, inclusive a **localização GPS** que o celular grava. A rotação é aplicada antes. Fotos maiores que 2560 pontos no lado maior são reduzidas. |
| HEIC | é o formato da câmera do iPhone, que o Chrome do Android não exibe. O backend converte para JPEG; o tipo e o tamanho gravados no banco são os do arquivo convertido. |
| Onde ficam | arquivos em `backend\storage\veiculos\<id do veículo>\` (fora do Git), com nome gerado pelo backend. O banco guarda só os metadados. Para mudar a pasta: `PASTA_FOTOS` no `.env`. |
| Acesso | a pasta não é pública. A imagem sai por `/api/veiculos/{id}/fotos/{id}/arquivo`, que confere a sessão e o dono a cada pedido. Conhecer o endereço não dá acesso. |
| Capa | no máximo uma por veículo (índice único no banco). A troca bloqueia a linha do veículo, então duas trocas simultâneas acontecem em sequência. |
| Câmera | "Tirar foto" abre a câmera do celular; "Da galeria" abre os arquivos. Funciona em HTTP na rede local (o teste no celular fica para a etapa 10). |

O vínculo da foto com manutenção, diagnóstico ou projeto entra nas etapas 4, 5 e 8.

### 11.4 Backup das fotos

O backup do banco (`gerenciar.py backup`) **não inclui as fotos**. Copie também
a pasta `backend\storage`. Exemplo (pasta `meu-veiculo`):

```powershell
Copy-Item -Recurse backend\storage D:\backup\meu-veiculo-fotos
```

### 11.5 Arquivos órfãos

O arquivo é gravado antes da linha no banco e apagado depois dela. Se o
computador desligar no meio, pode sobrar um arquivo sem registro (ninguém
consegue acessá-lo, mas ocupa espaço). Para conferir (pasta `backend`):

```powershell
.\.venv\Scripts\python.exe gerenciar.py limpar-fotos
```

O comando só **lista**: arquivos sem registro com mais de 1 hora, e fotos do
banco cujo arquivo sumiu. Para apagar os arquivos sem registro:

```powershell
.\.venv\Scripts\python.exe gerenciar.py limpar-fotos --apagar
```

### 11.6 Se a migration 0003 parar por causa de placas antigas

Ela lista, por exemplo: `usuário 3: ficariam com a mesma placa 'ABC1234':
veículos 5 (ABC-1234), 9 (abc1234)`. Nada foi alterado. Confira qual cadastro
é o correto e corrija a placa do outro à mão (por exemplo, no pgAdmin). Não
apague nem una veículos sem conferir os registros de cada um. Depois rode de
novo `gerenciar.py migrar`.

Se a migration avisar `o km atual era X, mas há registro com Y km`, ela
seguiu em frente: a quilometragem atual passou a ser a maior leitura. Confira
na tela Quilometragem de onde veio cada leitura e corrija o registro errado,
se houver.

## 12. Manutenção

### 12.1 Planos e pendências

Um plano é o que se repete ("troca de óleo a cada 10.000 km ou 12 meses").
Ao criar, informe quando foi feita pela última vez (ou use "a partir de hoje"):
o prazo é contado dessa base e não anda sozinho com o calendário. A aba
**Pendentes** mostra cada obrigação uma vez: atrasada, próxima (faltam até
1.000 km ou 30 dias), em dia ou "dados insuficientes" (falta a base; o sistema
não afirma que está em dia sem saber).

### 12.2 Manutenções realizadas e agendadas

- **Realizada**: aconteceu; se tiver quilometragem, vira leitura do hodômetro.
- **Agendada**: ainda vai acontecer; não mexe na quilometragem, não tem
  garantia e não entra nas despesas até ser marcada como realizada.
- Garantia "até os 95.000 km" é o que o hodômetro vai marcar, não a distância.

### 12.3 Peças e mão de obra

No formulário da manutenção há duas áreas:

- **Peças**: toque em **+ Adicionar peça** e informe nome e valor
  (ex.: Filtro de óleo, 70,00). Repita para cada peça.
- **Mão de obra**: toque em **+ Adicionar mão de obra** (ex.: Troca do filtro
  de óleo, 20,00).

Cada linha tem **Remover**. Os subtotais e o total aparecem na hora, só como
prévia: quem calcula o total que fica gravado é o backend.

Regras:

- Com pelo menos um item, o total é **sempre** a soma dos itens. A tela não
  envia total, e o backend recusa um total enviado junto com itens. O próprio
  banco confere (migration 0005): um total diferente da soma nunca é gravado.
- Sem nenhum item, aparece o campo **Valor total** para informar só o total
  (ex.: lavagem, 50,00).
- Manutenções antigas têm só o total. Nada é dividido por suposição; se quiser,
  edite e detalhe os itens (o total passa a ser a soma deles).
- Em manutenção agendada, os valores aparecem como estimados.
- Apagar a manutenção apaga os itens dela.

### 12.4 Ver valores

No detalhe da manutenção, e em cada item da aba **Realizadas**, o botão
**Ver valores** abre um quadro com cada peça e cada mão de obra com o seu
valor, o total de peças, o total de mão de obra e o total da manutenção. Se a
manutenção tem só o total, o quadro avisa que não há detalhamento.

### 12.5 Aviso de banco desatualizado

Quando o código recebe uma migration nova, o banco de desenvolvimento precisa
de `gerenciar.py migrar`. Enquanto isso não acontece, a API responde a todas
as telas com a mensagem "O banco de dados está na versão X e o sistema
precisa da Y..." (HTTP 503), em vez de falhar no meio do uso. Ao iniciar, o
backend também escreve esse aviso no terminal. A tela **Situação do sistema**
continua funcionando e mostra as migrations pendentes.

Na pasta `backend`:

```powershell
.\.venv\Scripts\python.exe gerenciar.py migrar
```

Não é preciso reiniciar o backend. Se você voltar o banco para uma versão
anterior (restaurar um backup antigo) com o backend ligado, reinicie o backend.

### 12.6 Se a migration 0004 parar por causa de vínculos entre veículos

Ela lista, por exemplo: `manutenção 8 (veículo 2) está ligada ao plano 5, que
é do veículo 3`. Nada foi alterado. Confira no pgAdmin qual vínculo está
errado e corrija à mão (o plano certo, ou deixe a manutenção avulsa com
`plano_id` vazio). Não apague registros sem conferir. Depois rode de novo
`gerenciar.py migrar`.

## 13. Diagnóstico (problemas do veículo)

### 13.1 Registrar um problema

Na aba **Diagnóstico**, toque em **+** e conte o que está acontecendo
("Barulho na suspensão dianteira"), os detalhes, o sistema e a gravidade:

| Gravidade | Orientação mostrada |
|---|---|
| Baixa | Pode esperar a próxima revisão. |
| Média | Resolver nas próximas semanas. |
| Alta | Resolver o quanto antes. |
| Crítica | Evite usar o veículo até resolver. |

A data não pode ser no futuro. A quilometragem é opcional; se informada,
vira uma leitura do hodômetro (como na manutenção) e precisa combinar com as
outras leituras.

### 13.2 Situações

- **Aberto** e **Em observação**: o problema existe. "Em observação" é só um
  lembrete de que está sendo acompanhado; os dois aparecem em **Abertos** e em
  **Precisa de atenção**, no Início (dos mais graves para os menos graves).
- **Resolvido**: resolvido por uma manutenção **realizada** do mesmo veículo.
  A data de resolução é a data da manutenção.
- **Descartado**: não era problema ou sumiu sozinho. O motivo é opcional.
- **Reabrir** volta para aberto. A manutenção que tinha resolvido continua no
  histórico, só deixa de estar ligada.

A situação não é escolhida no formulário: ela muda pelos botões do detalhe.
Cada mudança automática deixa uma anotação ("Resolvido com a manutenção...",
"Reaberto: ...").

### 13.3 Resolver com uma manutenção

No detalhe do diagnóstico:

- **Resolver com uma manutenção**: abre "Nova manutenção" com a faixa
  "Resolvendo o diagnóstico" e o sistema já escolhido. Ao salvar:
  - **Já foi feita** → a manutenção é gravada e o diagnóstico fica resolvido,
    de uma vez só. Se qualquer parte falhar, nada é gravado.
  - **Agendar** → a manutenção fica ligada como a prevista; o diagnóstico
    continua aberto e é resolvido sozinho quando ela for marcada como realizada.
- **Usar uma manutenção já registrada**: escolha uma manutenção do mesmo
  veículo (realizada resolve; agendada fica como prevista).
- A manutenção que resolve não pode ter data anterior à do problema.
- Tocar duas vezes em salvar não cria duas manutenções: o segundo envio recebe
  "Este diagnóstico já foi resolvido".

O que acontece depois, pela manutenção:

| Na manutenção | No diagnóstico |
|---|---|
| Agendada marcada como realizada | Resolvido, com a data dela |
| Realizada volta para agendada | Reaberto (a manutenção continua ligada, como prevista) |
| Realizada apagada | Reaberto, sem manutenção ligada |
| Agendada apagada | Continua aberto, sem manutenção prevista |
| Data da realizada alterada | A data de resolução acompanha |

O detalhe e a edição da manutenção avisam disso antes de salvar ou apagar.

### 13.4 Aviso de garantia

Se uma manutenção realizada do **mesmo sistema** estava em garantia na data do
problema (pela data ou pelo limite de km, o que vier primeiro), o detalhe
mostra "Há peça em garantia neste sistema". É um aviso para conferir com a
oficina, não uma garantia de cobertura. Garantia só por km, em problema sem
quilometragem, não é mostrada (não dá para saber).

### 13.5 Anotações e fotos

- Anotações: texto e data (hoje, por padrão), da mais recente para a mais
  antiga. Dá para apagar uma anotação.
- Fotos: no detalhe, **Adicionar** abre "Nova foto" já ligada ao diagnóstico.
  Na galeria, o filtro **Diagnósticos** mostra só essas. Uma foto fica ligada
  a uma manutenção **ou** a um diagnóstico, nunca aos dois.
- Apagar o diagnóstico apaga as anotações e as fotos dele (inclusive os
  arquivos). A manutenção ligada continua registrada.

Diagnóstico não tem valor próprio: o custo fica na manutenção que o resolveu.

### 13.6 Se a migration 0006 parar por causa de vínculos antigos

Ela lista, por exemplo:

- `diagnóstico 4 (veículo 2) está ligado à manutenção 9, que é do veículo 3`;
- `foto 12 (veículo 2) está ligada ao diagnóstico 4, que é do veículo 3`;
- `diagnóstico 5 (resolvido) está ligado à manutenção 7, que está agendada`.

Nada foi alterado. Confira no pgAdmin e corrija à mão: o vínculo certo, ou
deixe `manutencao_id` / `diagnostico_id` vazio; para o terceiro caso, ou a
manutenção foi mesmo feita (mude-a para `realizada`) ou o diagnóstico ainda
está aberto (mude para `aberto` e deixe `data_resolucao` vazia). Não apague
registros sem conferir. Depois rode de novo `gerenciar.py migrar`.

## 14. Finanças e gastos

### 14.1 O que entra no total do mês

O total da aba **Gastos** soma só o que realmente saiu do bolso, cada valor
uma vez, pela tabela de origem:

| Entra no total | Pela data |
|---|---|
| Manutenção **realizada** (o total dela, com peças e mão de obra) | da manutenção |
| Abastecimento | do abastecimento |
| Gasto **pago** | do **pagamento** |
| Item de projeto (inclusive de projeto cancelado: a despesa aconteceu) | do item |

Não entram: manutenção **agendada** e gasto **pendente**. Eles aparecem
separados, no quadro **Previsto (não entra no total)** do mês e nas listas
**Vencidas** e **A vencer**. Nenhuma cópia em gasto é criada para uma
manutenção ou um abastecimento: o valor já conta pela tabela de origem.

Exemplo: estacionamento pago de R$ 30,00 + troca de óleo realizada de
R$ 350,00 = R$ 380,00. Uma manutenção agendada de R$ 120,00 no mesmo mês fica
no "Previsto" e o total continua R$ 380,00.

### 14.2 Mês do gasto pago

Um gasto pago entra no mês da **data do pagamento**. Exemplo: seguro lançado
em 24/09 como pendente (vence 10/11) e pago em 08/11 entra em **novembro**.

- No "Novo gasto" com **Já foi pago** ligado, a data do pagamento acompanha a
  data do gasto (dá para mudar).
- Em **Vencidas**/**A vencer**, **Marcar como pago** pergunta a data
  (padrão: hoje).
- Gastos pagos registrados antes desta versão podem não ter a data do
  pagamento. Ela não é inventada: esses contam pela data do gasto, e a tela
  avisa "Não informada (gasto antigo)".

### 14.3 Contas pendentes

Gasto pendente exige **vencimento** (o banco também confere). Ele aparece em:

- **Vencidas**: vencimento antes de hoje ("há 3 dias");
- **A vencer**: vence hoje ou depois ("em 47 dias").

As listas mostram todas as contas pendentes do veículo, de qualquer mês.

### 14.4 Por categoria e arredondamento

Os totais são somados pelo PostgreSQL (`numeric`, sem arredondar). O
percentual de cada categoria é calculado no backend com `Decimal`,
arredondado para inteiro **meio para cima** (12,5% vira 13%). Por isso a soma
dos percentuais pode dar 99% ou 101%. Mês sem despesas mostra R$ 0,00 e
nenhuma categoria (não inventa percentuais).

### 14.5 Navegação: Mês, Ano e Total

Na aba **Gastos**, escolha o período:

- **Mês**: as setas trocam o mês ("Setembro de 2026").
- **Ano**: o ano inteiro, de 1º de janeiro a 31 de dezembro ("Ano de 2026");
  as setas trocam o ano.
- **Total**: tudo desde o primeiro registro do veículo, sem setas.

O total, as categorias, o "Previsto" e os lançamentos seguem o período
escolhido, com as mesmas regras (gasto pago pela data do pagamento, nada
contado duas vezes). Não é possível ir além do mês ou do ano atual. As contas
**Vencidas** e **A vencer** são sempre todas as pendentes, de qualquer período.

- Tocar num lançamento abre a manutenção, o gasto ou o abastecimento. Itens de
  projeto ganham tela na etapa 8 (por enquanto aparecem sem link).

### 14.6 Se a migration 0007 parar por causa de gastos pendentes sem vencimento

Ela lista, por exemplo: `gasto 4 (veículo 2, seguro, R$ 2400.00, lançado em
18/09/2026) está pendente e sem vencimento`. Nada foi alterado. No pgAdmin,
informe a `data_vencimento` desse gasto ou, se ele já foi pago, marque
`pago = true`. Depois rode de novo `gerenciar.py migrar`.

## 15. Abastecimentos e consumo

### 15.1 Registrar um abastecimento

Em **Finanças → Combustível**, toque em **+**. Informe combustível, tipo,
data, quilometragem, preço e quantidade.

O que aparece depende do tipo do veículo (escolhido no cadastro dele):

| Veículo | Combustíveis no abastecimento |
|---|---|
| Flex | gasolina, etanol |
| Gasolina / Etanol / Diesel | só o próprio |
| GNV | GNV, gasolina, etanol |
| Híbrido | gasolina, eletricidade (recarga do plug-in) |
| Elétrico | eletricidade (recarga) |

Tipos e unidade de cada combustível:

| Combustível | Tipos | Unidade |
|---|---|---|
| Gasolina | Comum; Comum aditivada; Premium; Premium aditivada | litro (L) |
| Etanol | Comum (hidratado); Aditivado; Premium; Premium aditivado | litro (L) |
| Diesel | S10; S10 aditivado; S500; S500 aditivado | litro (L) |
| GNV | sem tipo | metro cúbico (m³) |
| Eletricidade | Recarga AC; Recarga DC | kWh |

Na eletricidade, "Tanque cheio" vira **Carga completa** (bateria a 100%).

- A quilometragem é obrigatória e vira leitura do hodômetro (precisa combinar
  com as outras). Abastecimentos antigos podem ser lançados depois.
- **Tipo**: obrigatório (não aparece no GNV). Abastecimentos registrados
  antes desse campo ficam "não informado"; ao editar, escolha se souber. Para
  o consumo, os tipos do mesmo combustível contam juntos (gasolina comum e
  premium são gasolina). Num híbrido, gasolina e recarga entre dois "cheios"
  são mistura: aquele ciclo fica sem consumo.
- Marque **Tanque cheio** quando encher o tanque: é assim que o consumo é
  calculado. Parcial = deixe desligado.
- **Recentes** mostra os postos usados por último.

### 15.2 Valor total e cupom

O total é calculado pelo backend: litros × preço, arredondado para centavos
meio para cima. Exemplo: 38,5 L × R$ 4,29 = 165,165 → **R$ 165,17**. A tela
mostra uma prévia, mas o valor gravado é o do backend.

Se o cupom da bomba mostrar outro valor, toque em **Corrigir pelo cupom** e
digite. Ele é aceito quando a diferença para o calculado é de até **R$ 50,00**
(e é ele que entra nas despesas). O campo mostra o valor calculado ao lado,
para conferir: com essa folga, um erro de digitação de até R$ 50,00 passa sem
aviso. Diferença maior é recusada. O banco confere a mesma regra (migration
0009; até a 0008 a tolerância era de R$ 0,10).

### 15.3 Como o consumo é calculado

Entre dois abastecimentos de **tanque cheio**:

- distância = km do cheio final − km do cheio inicial;
- quantidade = o que foi abastecido **depois** do cheio inicial, até o cheio
  final inclusive (os parciais do meio e o cheio final). A quantidade do cheio
  inicial não entra.

Exemplo: cheio aos 10.000 km; parcial de 10 L aos 10.100 km; cheio de 20 L
aos 10.300 km → 300 / (10 + 20) = **10 km/L**.

- O primeiro tanque cheio sozinho não dá consumo ("Primeiro tanque cheio").
- Parcial antes do primeiro cheio fica "Fora do cálculo".
- Ciclo com **mistura de combustíveis** (por exemplo, tanque com gasolina
  completado com etanol) ou em que a quilometragem não aumentou fica "Sem
  consumo" e não entra na média. O detalhe do abastecimento diz o motivo.
- A média de cada combustível é a distância total dividida pela quantidade
  total dos ciclos válidos (nunca a média simples dos km/L).
- No mesmo dia, a ordem é a da quilometragem. Incluir, editar ou apagar um
  abastecimento recalcula os ciclos afetados na hora.
- Sem ciclos válidos, a tela diz "Ainda não há consumo calculado" (não mostra
  zero).

### 15.4 Etanol ou gasolina?

Só para veículo flex. O limite vem do consumo real do **seu** carro:
consumo do etanol ÷ consumo da gasolina (ex.: 7,9 ÷ 11,3 = **70%**). Não é
usado um percentual fixo.

- Compara com o último preço pago de cada combustível: se o etanol custou
  menos que o limite (ex.: R$ 4,29 ÷ R$ 6,25 = 69%), "Hoje, o etanol compensa".
- **Simular com os preços de hoje**: digite os preços da bomba e toque em
  **Comparar**. Nada é gravado.
- Sem a média dos dois combustíveis, a tela explica o que falta (é preciso
  ter pelo menos dois tanques cheios de cada um).

### 15.5 Finanças

Cada abastecimento entra uma vez nas despesas, na categoria **Combustível**,
pela data dele. Tocar no lançamento abre o abastecimento.

### 15.6 Se a migration 0008 ou a 0010 parar por causa de abastecimentos antigos

**0010** (tipos de cada combustível): ela converte sozinha gasolina
"aditivada" em "comum aditivada" e etanol "aditivada" em "aditivado". Diesel
com "comum" ou "aditivada" não diz se era S10 ou S500: ela lista, por exemplo,
`abastecimento 7 (veículo 2, 20/09/2026): diesel "aditivada"`, e para sem
alterar nada. No pgAdmin, troque o `tipo` para `s10`, `s10_aditivado`, `s500`
ou `s500_aditivado` (ou deixe vazio, "não informado") e rode de novo
`gerenciar.py migrar`.

**0008** (total coerente):

Ela lista, por exemplo: `abastecimento 5 (veículo 2, 15/09/2026): 38.500 ×
R$ 4.290 = R$ 165.17, mas o total gravado é R$ 16.52`. Nada foi alterado.
Confira o cupom e corrija no pgAdmin os litros, o preço ou o `valor_total`
desse abastecimento. Depois rode de novo `gerenciar.py migrar`.
