# Meu Veículo

Aplicação para cada usuário acompanhar seus veículos, gastos, abastecimentos,
manutenções, diagnósticos, projetos de melhoria e fotos. É uma aplicação web
responsiva e instalável (PWA), feita com React + TypeScript no frontend,
FastAPI (Python) no backend e PostgreSQL no banco de dados.

> **Estado atual: etapa 10 (revisão integrada, celular e README final).**
> Todos os módulos do pedido estão implementados: contas e permissões,
> veículos e quilometragem, fotos, manutenções e planos, diagnósticos,
> finanças, abastecimentos e consumo (com tanque e marcador), projetos,
> Início, histórico e administração. O uso pelo celular na rede de casa está
> na seção 18, e a lista do que foi testado e do que depende do seu ambiente,
> na seção 19. Situação de cada etapa: `docs/progresso.md`.

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
12. [Manutenção](#12-manutenção)
13. [Diagnóstico (problemas do veículo)](#13-diagnóstico-problemas-do-veículo)
14. [Finanças e gastos](#14-finanças-e-gastos)
15. [Abastecimentos e consumo](#15-abastecimentos-e-consumo)
16. [Projetos de melhoria](#16-projetos-de-melhoria)
17. [Início, custo do veículo, histórico e administração](#17-início-custo-do-veículo-histórico-e-administração)
18. [Usar pelo celular (rede local) e instalar como aplicativo](#18-usar-pelo-celular-rede-local-e-instalar-como-aplicativo)
19. [O que foi testado e o que depende do seu ambiente](#19-o-que-foi-testado-e-o-que-depende-do-seu-ambiente)
20. [Dados de exemplo para apresentação](#20-dados-de-exemplo-para-apresentação)

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
│   ├── demonstracao/            carga OPCIONAL de dados de exemplo (seção 20)
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
    ├── vite.config.ts           servidor de desenvolvimento, proxy /api e porta 4173
    ├── public/                  manifesto da PWA, ícones, service worker (sw.js) e página "sem conexão"
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
- **Banco (PostgreSQL)**: guarda todos os dados, inclusive as imagens das fotos. **Só o backend acessa o banco.** O celular nunca recebe endereço, usuário ou senha do PostgreSQL.

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
Se qualquer parte falhar, nada é gravado. Exemplo (resolver um diagnóstico com uma manutenção nova, etapa 5):

```python
with self.uow.transacao():
    manutencao = self.manutencoes.criar(dados)
    self.diagnosticos.resolver(diagnostico_id, manutencao.id)
```

### 3.5 Como acrescentar um endpoint (roteiro)

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
| `pages/` | uma tela inteira por endereço (`LoginPage`, `InicioPage`, `VeiculoDetalhePage`, `ManutencaoPage`, `DiagnosticoPage`, `FinancasPage`, `AbastecimentoFormPage`, `ProjetoDetalhePage`, `HistoricoPage`, `AdminPage`, `MaisPage`...) e os testes de tela (`*.test.tsx`) |
| `components/` | peças visuais reaproveitáveis (`CampoTexto`, `CampoSenha` com o olho, `BotaoEnviar`, `Alerta`, `TopoComVoltar`, `RotaProtegida`, `BarraNavegacao`, `Formulario` com opções/chave/diálogo de confirmação, `PecasVeiculo` com placa/hodômetro/foto...) |
| `contexts/` | `AuthContext`: quem está logado. `VeiculosContext`: os veículos da conta e o veículo em uso. Ficam só na memória da página (nada em `localStorage`). |
| `hooks/` | `useEnvioFormulario`: "enviando", trava contra envio duplicado e erros da API por campo. `useVeiculoDaRota`: carrega o veículo do endereço. |
| `services/` | conversa com a API. `apiCliente.ts` é o único lugar que chama `fetch` e envia o cabeçalho `X-MV-Requisicao`. |
| `types/` | formatos dos dados, iguais aos schemas do backend |
| `utils/` | funções auxiliares. `datas.ts` formata datas **sem** `new Date()`, para não voltar um dia por causa do fuso. `formatos.ts` trata km, placa e dinheiro (dinheiro sempre como texto, nunca ponto flutuante). `pwa.ts` registra o service worker. |
| `styles/` | `tema.css` com as cores do PDF (verde-petróleo, fundo claro, cartões) e um arquivo por módulo (`veiculos.css`, `manutencao.css`, `diagnostico.css`, `financas.css`, `painel.css`) |

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

Para abrir pelo celular, veja a seção 18. Lembre: no celular, `localhost` é o
próprio celular, não o seu computador.

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
npm run build
```

O `npm run build` gera a versão final em `frontend\dist\` (a mesma usada
pelo `npm run app:celular`). O aviso `Some chunks are larger than 500 kB` é
só uma sugestão de otimização: o arquivo tem cerca de 140 kB comprimido e
não impede nada.

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
| Foto aparece como "Imagem indisponível" | foto antiga cujo arquivo já não estava na pasta quando as fotos foram para o banco (0013) | seção 11.5 |
| Tela mostra `O banco de dados está na versão 0004 e o sistema precisa da 0005...` (HTTP 503) | o código foi atualizado com uma migration nova e o banco ainda não | `.\.venv\Scripts\python.exe gerenciar.py migrar` (pasta `backend`); não precisa reiniciar o backend (seção 12.5) |
| `coluna ... não existe` (erro 500) no terminal do backend | mesma causa, em versão antiga do código sem o aviso 503 | `.\.venv\Scripts\python.exe gerenciar.py migrar` (pasta `backend`) |
| Ao salvar a manutenção aparece "A data não pode ser anterior" | ela resolve um diagnóstico identificado depois dessa data | corrija a data da manutenção ou a do diagnóstico (seção 13.3) |
| `gerenciar.py migrar` para na 0006 com uma lista de diagnósticos ou fotos | vínculos antigos entre veículos diferentes ou incoerentes | corrija os vínculos listados (seção 13.6); nada foi alterado |
| `gerenciar.py migrar` para na 0007 com uma lista de gastos pendentes | gastos antigos pendentes sem vencimento | informe o vencimento ou marque como pago (seção 14.6); nada foi alterado |
| `gerenciar.py migrar` para na 0008 com uma lista de abastecimentos | total gravado muito diferente de litros × preço | corrija litros, preço ou total (seção 15.6); nada foi alterado |
| `gerenciar.py migrar` para na 0011 com uma lista de projetos ou fotos | projeto concluído sem data, data de conclusão em projeto aberto ou foto ligada a projeto de outro veículo | corrija os registros listados (seção 16.6); nada foi alterado |
| "Este projeto está concluído. Reabra o projeto para alterar os gastos." | gastos só mudam com o projeto planejado ou em andamento | toque em **Reabrir projeto**, ajuste e conclua de novo (seção 16.2) |
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
- Cada service também confere a quem pertence cada veículo e registro (`services/acesso_veiculo.py`), sem confiar em IDs enviados pela tela, e se os registros ligados entre si são do mesmo veículo. Veículo de outra pessoa responde 404, como se não existisse.

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

### 10.2 Envio real pelo Gmail (modo "smtp")

Com `EMAIL_MODO=smtp`, as mensagens de "Esqueci a senha" e os convites saem de
verdade por uma conta do Gmail. O Gmail não aceita a senha normal da conta
para isso: ele exige uma **senha de app**, uma senha de 16 letras criada só
para o Meu Veículo, que você pode apagar quando quiser sem mexer na senha da
conta.

**Passo 1. Escolha a conta que vai enviar.** Recomendo criar um Gmail só para
o sistema (por exemplo, `meuveiculo.suaconta@gmail.com`). Assim, a senha de
app guardada no `backend\.env` não dá acesso ao seu e-mail pessoal. Usar a
sua conta pessoal também funciona.

**Passo 2. Ligue a verificação em duas etapas** dessa conta (o Google só
oferece senha de app com ela ligada): https://myaccount.google.com/security →
**Verificação em duas etapas** → siga as telas.

**Passo 3. Crie a senha de app:** https://myaccount.google.com/apppasswords →
nome do app: `Meu Veículo` → **Criar**. O Google mostra 16 letras em quatro
grupos (`abcd efgh ijkl mnop`). Copie **sem os espaços**. Ela só aparece uma
vez; se perder, apague e crie outra.

**Passo 4. Preencha o `backend\.env`** (abra no VS Code; não cole o conteúdo
dele em conversas nem no Git):

```
EMAIL_MODO=smtp
EMAIL_REMETENTE=Meu Veículo <meuveiculo.suaconta@gmail.com>
SMTP_HOST=smtp.gmail.com
SMTP_PORTA=587
SMTP_SEGURANCA=starttls
SMTP_USUARIO=meuveiculo.suaconta@gmail.com
SMTP_SENHA=abcdefghijklmnop
URL_FRONTEND=http://localhost:5173
```

- `EMAIL_REMETENTE` precisa usar o **mesmo endereço** de `SMTP_USUARIO`; o
  nome antes dele ("Meu Veículo") é livre.
- `URL_FRONTEND` é o começo dos links das mensagens. Para os links abrirem no
  celular, use o IP do computador (seção 18.6) ou o endereço HTTPS (seção 18.8).

**Passo 5. Teste o envio** (pasta `meu-veiculo\backend`; o backend pode estar
ligado ou desligado). Mande para um endereço seu, de preferência outro que não
o da conta que envia:

```powershell
.\.venv\Scripts\python.exe gerenciar.py testar-email seu-email@exemplo.com
```

Esperado (a senha nunca é mostrada):

```
Modo: smtp
Servidor: smtp.gmail.com, porta 587, segurança starttls
Usuário: meuveiculo.suaconta@gmail.com; senha: preenchida
Remetente: Meu Veículo <meuveiculo.suaconta@gmail.com>
Links dos e-mails começam com: http://localhost:5173

Enviado para seu-email@exemplo.com. Confira a caixa de entrada (e a pasta de spam).
```

Se der errado, o comando diz o motivo e o que conferir, por exemplo
`ERRO: o e-mail não foi enviado. O servidor recusou o usuário ou a senha...`.
Antes de tentar, ele também confere o `.env` (servidor vazio, porta e
segurança trocadas, remetente diferente do usuário).

**Passo 6. Teste pelo sistema.** Reinicie o backend (ele só lê o `.env` ao
iniciar), abra **Esqueci a senha**, informe o e-mail de uma conta cadastrada e
confira a caixa de entrada. Por segurança, a tela mostra sempre a mesma
mensagem, exista a conta ou não; se o envio falhar, o terminal do backend
mostra só `Falha ao enviar e-mail (tipo do erro)`, sem destinatário nem
conteúdo. Para descobrir o motivo, use o `testar-email` do passo 5.

| Mensagem do `testar-email` | O que fazer |
|---|---|
| "recusou o usuário ou a senha" | confira se `SMTP_SENHA` é a senha de app (16 letras, sem espaços) e se `SMTP_USUARIO` é o endereço completo; crie outra senha de app se precisar |
| "Não encontrei o servidor" | confira `SMTP_HOST=smtp.gmail.com` e a internet |
| "não respondeu a tempo" | rede ou antivírus bloqueando a porta 587; teste em outra rede |
| "A conexão segura falhou" | use 587 com `starttls` (ou 465 com `ssl`). Antivírus com proteção de e-mail (como o Avast, que está no seu computador) pode atrapalhar: desligue por alguns minutos a verificação de e-mails enviados e teste de novo |
| "Modo arquivo: nada saiu do computador" | falta `EMAIL_MODO=smtp` no `.env` |
| a mensagem chegou na pasta de spam | comum nas primeiras mensagens de uma conta nova; marque "Não é spam" |

Para voltar ao modo de desenvolvimento, troque para `EMAIL_MODO=arquivo`. Para
desligar o acesso do sistema à conta, apague a senha de app em
https://myaccount.google.com/apppasswords.

Contas pessoais do Outlook/Hotmail ficaram de fora: a Microsoft está trocando o
login por senha no envio (SMTP) por outro método, que este sistema não usa.

**Situação de teste:** o envio por SMTP foi testado de ponta a ponta com um
servidor SMTP falso, dentro dos testes automáticos
(`backend\tests\test_envio_smtp.py`): login, entrega, senha recusada,
servidor desligado e configuração errada. O envio pelo **Gmail de verdade**
depende da sua conta e **não foi testado por mim**.

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
| Tamanho do tanque | litros, obrigatório (menos no elétrico, que não tem tanque). Veículos antigos sem ele recebem um aviso para atualizar. Veja a seção 15.3. |
| Dinheiro | o valor pago viaja como texto (`"65000.00"`) e é `Decimal` no backend. Mais de duas casas decimais é recusado, não arredondado em silêncio. |
| Veículo em uso | fica gravado na conta (vale em qualquer aparelho). O veículo recém-cadastrado vira o veículo em uso. |
| Inativar | para carro vendido. Nada é apagado: leituras, fotos e registros continuam consultáveis. O veículo inativo fica somente para leitura até ser reativado. Não existe "apagar veículo". |
| Permissão | quem não é o dono (nem admin) recebe "Veículo não encontrado", a mesma resposta de um veículo que não existe. |

### 11.2 Quilometragem

Cada atualização é uma **leitura**: o valor e o dia em que o hodômetro marcava
esse valor. A tabela `leitura_km` guarda também quando a leitura foi digitada.

**Atualizar km pede o nível do combustível** (regra de negócio, conferida no
backend): em todo veículo com tanque, a tela "Atualizar km" pede também como
está o marcador (vazio, 0,5/4 ... cheio). A leitura entra como **marcação do
tanque** (seção 15.3), que é mais um ponto do cálculo do consumo e também
resolve o aviso "marcação do mês". Sem o nível, o backend recusa
("Informe o nível do combustível"). Exceções:

- veículo **elétrico** (não tem tanque): só o km, como antes;
- veículo antigo **sem o tamanho do tanque** no cadastro: a tela pede para
  completar o cadastro antes ("Completar cadastro"), porque é o tamanho que
  transforma o nível em litros.

Uma leitura feita assim é corrigida **editando a marcação** (o histórico mostra
o link "edite a marcação do tanque"), como as leituras de abastecimento.

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
3. O banco recalcula a quilometragem atual na hora. Os indicadores
   (consumo, custo por km, planos) são sempre calculados a partir das
   leituras válidas, então refletem a correção.

"Anular" retira uma leitura que não deveria existir (não é possível anular a
única leitura do veículo). "Corrigir" e "Anular" valem para a leitura do
cadastro, as herdadas e as do elétrico. Leituras que vieram de um
abastecimento, manutenção, diagnóstico ou marcação do tanque (inclusive as do
"Atualizar km" com nível) são corrigidas editando esse registro.

### 11.3 Fotos

| Item | Regra |
|---|---|
| Formatos | JPEG, PNG, WebP e HEIC, até 10 MB (10.485.760 bytes). |
| Conferência | o backend identifica o formato pelos primeiros bytes do arquivo e abre a imagem inteira. A extensão e o tipo informado pelo navegador não são levados em conta. |
| Regravação | a imagem é regravada do zero: somem conteúdos escondidos e os metadados, inclusive a **localização GPS** que o celular grava. A rotação é aplicada antes. Fotos maiores que 2560 pontos no lado maior são reduzidas. |
| HEIC | é o formato da câmera do iPhone, que o Chrome do Android não exibe. O backend converte para JPEG; o tipo e o tamanho gravados no banco são os do arquivo convertido. |
| Onde ficam | **no PostgreSQL** (desde a migration 0013): a imagem na tabela `foto_conteudo` e os dados da foto (legenda, data, capa, vínculo) em `veiculo_foto`. Nenhum arquivo é gravado em pasta. A imagem fica numa tabela separada para a galeria listar as fotos sem carregar as imagens. |
| Acesso | a pasta não é pública. A imagem sai por `/api/veiculos/{id}/fotos/{id}/arquivo`, que confere a sessão e o dono a cada pedido. Conhecer o endereço não dá acesso. |
| Capa | no máximo uma por veículo (índice único no banco). A troca bloqueia a linha do veículo, então duas trocas simultâneas acontecem em sequência. |
| Câmera | "Tirar foto" abre a câmera do celular; "Da galeria" abre os arquivos. Funciona também em `http://` na rede local, porque usa o campo de arquivo do navegador, não o acesso direto à câmera (seção 18). |

Fotos também podem ser ligadas a uma manutenção, a um diagnóstico ou a um
projeto (antes e depois), sempre do mesmo veículo (seções 12, 13 e 16).

### 11.4 Backup das fotos

As fotos estão no banco, então o backup do banco já as inclui (pasta `backend`):

```powershell
.\.venv\Scripts\python.exe gerenciar.py backup
```

Cada foto ocupa de 0,2 a 1 MB no banco (o backend reduz e regrava a imagem no
envio), por isso o arquivo de backup cresce junto com a galeria.

### 11.5 Fotos que estavam na pasta `backend\storage` (antes da 0013)

Até a etapa 10, as imagens ficavam na pasta `backend\storage`. A migration
0013 (aplicada pelo `gerenciar.py migrar`) **copia cada imagem dessa pasta
para o banco** e não apaga nada. No terminal ela mostra, por exemplo:
`0013: 6 de 6 fotos copiadas da pasta ... para o banco`.

- Se alguma foto não tinha arquivo na pasta, ela aparece na lista do terminal e
  continua na galeria como "Imagem indisponível" (nada é inventado).
- Se o arquivo aparecer depois (por exemplo, `PASTA_FOTOS` apontava para outra
  pasta, ou você restaurou a pasta de um backup), rode (pasta `backend`):

  ```powershell
  .\.venv\Scripts\python.exe gerenciar.py importar-fotos
  ```

  Ele copia para o banco só as fotos que ainda estão sem imagem, nunca troca
  uma imagem que já está no banco e não apaga nada. Para ler outra pasta:
  `... gerenciar.py importar-fotos --pasta D:\caminho\da\pasta`.
- Depois de conferir no app que todas as fotos aparecem, a pasta
  `backend\storage` pode ser apagada: o sistema não lê mais dela.

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

### 14.3 Gastos futuros e contas pendentes

Um gasto que ainda vai acontecer (por exemplo, **IPVA 2027, R$ 1.645,00,
vencimento em 13/05/2027**) é lançado assim:

1. Finanças → **Lançar gasto futuro** (ou o "+" e desligue **Já foi pago**).
2. Informe valor, categoria, descrição e a **Data prevista (vencimento)**, que
   pode ser em qualquer dia do futuro.

Ele aparece em:

- **Gastos futuros** (Finanças): vencem hoje ou depois ("em 223 dias"), com o
  total no título;
- **Vencidas** (Finanças): a data passou e ainda não foi pago ("há 3 dias");
  também em "Precisa de atenção" no Início;
- **Próximos gastos** (Início): o total, a quantidade e os três mais próximos,
  com o link "Ver todos".

Gasto futuro **não entra** nas despesas nem nos gastos do mês: só conta quando
você toca em **Marcar como pago**, no mês do pagamento. As listas mostram
todos os gastos pendentes do veículo, de qualquer mês (o banco exige a data
prevista em todo gasto não pago).

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
data, quilometragem e **dois** destes três: preço por litro, litros, valor
total (o terceiro é calculado, veja 15.2). Opcional: o nível do marcador antes
de abastecer (15.3).

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

### 15.2 Litros, preço e valor total (dois dos três)

Em **Calcular automaticamente**, escolha o que a tela calcula; os outros dois
você digita:

| Calcular | Você digita | Conta (feita pelo backend) |
|---|---|---|
| Valor total (padrão) | preço e litros | total = litros × preço, centavos meio para cima |
| Litros | preço e valor total | litros = total ÷ preço, 3 casas meio para cima |
| Preço | litros e valor total | preço = total ÷ litros, 3 casas meio para cima |

Exemplos: 38,5 L × R$ 4,29 = 165,165 → **R$ 165,17**; R$ 250,00 ÷ R$ 6,25 =
**40 L**; R$ 100,00 ÷ R$ 5,79 = 17,2711... → **17,271 L**. Quando a tela
calcula os litros ou o preço, o valor total gravado é o que você digitou (o da
bomba). A tela mostra uma prévia, mas o valor gravado é o do backend.

Se o cupom da bomba mostrar outro valor, toque em **Corrigir pelo cupom** e
digite. Ele é aceito quando a diferença para o calculado é de até **R$ 50,00**
(e é ele que entra nas despesas). O campo mostra o valor calculado ao lado,
para conferir: com essa folga, um erro de digitação de até R$ 50,00 passa sem
aviso. Diferença maior é recusada. O banco confere a mesma regra (migration
0009; até a 0008 a tolerância era de R$ 0,10).

### 15.3 Tamanho do tanque e nível do marcador

**Tamanho do tanque** (em litros, está no manual) é obrigatório no cadastro e
na edição do veículo, menos no elétrico. Veículos cadastrados antes dele
continuam funcionando, mas o Início, a tela do veículo e a aba Combustível
pedem para informar (**Editar veículo → Tamanho do tanque**).

Para que serve:

- **Não passar do limite do tanque**: litros acima do que cabe são
  recusados como erro de digitação. Sem o nível: até o tanque + 10% (o tanque
  real leva um pouco mais que o manual, contando o bocal; 56 L → até 61,6 L).
  Com o nível: o espaço livre pelo marcador + 1/8 do tanque de folga (1/4 num
  tanque de 56 L → livres 42 L, aceita até 49 L). A tela avisa antes de salvar.
- **Nível do marcador** antes de abastecer (opcional; só gasolina, etanol e
  diesel): botões 0, ½, 1, 1½ ... 4, em quartos do tanque, como você lê
  ("1,5/4" = 1½). A tela mostra quanto cabe e quanto custa encher.
- **Marcação do tanque** (sem abastecer): **Marcar km e nível** na aba
  Combustível. A ideia é uma vez no **início de cada mês**; enquanto a deste
  mês não for feita, o Início e a aba Combustível lembram. A quilometragem
  vira leitura do hodômetro (como no abastecimento) e apagar a marcação
  retira a leitura.

**Nível do tanque** (cartão no Início e na aba Combustível, e lembrete no
formulário de abastecimento, ao lado do marcador):

- Vem do registro mais recente do tanque: a marcação (inclusive a do
  "Atualizar km"), o abastecimento de tanque cheio (= cheio) ou o abastecimento
  parcial com o nível antes (nível antes + litros abastecidos). GNV e recarga
  elétrica não mexem nesse tanque.
- Se o carro rodou depois desse registro e já existe consumo médio, a tela
  mostra a **estimativa de agora**, com "≈": litros gastos = km rodados ÷ km/L.
  Ex.: cheio (56 L) e 500 km a 12,5 km/L → 40 L gastos → sobram 16 L → ≈ 1/4.
- Sem registro, ou se o último abastecimento foi parcial e sem o nível, mostra
  "Dados insuficientes" e o motivo (nunca um nível inventado).

### 15.4 Como o consumo é calculado

O consumo é medido entre dois **pontos** em que se sabe quanto combustível
havia no tanque:

| Ponto | O que se sabe | Exatidão |
|---|---|---|
| Tanque cheio | depois de abastecer, o tanque está cheio | exato (referência) |
| Abastecimento com nível | antes, faltava tanque × (4 − nível) / 4 | ± meio oitavo do tanque |
| Marcação do tanque | faltava tanque × (4 − nível) / 4 | ± meio oitavo do tanque |

Num tanque de 56 L, cada leitura do marcador tem margem de **± 3,5 L**. Essa
margem cobre a leitura; marcadores de carro não são perfeitamente lineares,
por isso o **tanque cheio continua sendo o mais exato**.

Exemplo com o marcador (tanque de 56 L): marcação em 3/4 aos 84.000 km (faltam
14 L); 280 km depois, enche com 42 L. Consumo = 280 / (42 − 14) = **10 km/L**,
e com a margem fica **entre 8,9 e 11,4 km/L**. A tela mostra "≈ 10,0 km/L" e a
faixa.

Quanto mais longo o período, menor a margem: em trechos seguidos, a leitura
do marcador do meio entra somando num trecho e subtraindo no outro e se anula.
Só as pontas sobram. Por isso a média e o **consumo por mês** ficam bons
mesmo usando o marcador.

Entre dois abastecimentos de **tanque cheio** (o caso exato):

- distância = km do cheio final − km do cheio inicial;
- quantidade = o que foi abastecido **depois** do cheio inicial, até o cheio
  final inclusive (os parciais do meio e o cheio final). A quantidade do cheio
  inicial não entra.

Exemplo: cheio aos 10.000 km; parcial de 10 L aos 10.100 km; cheio de 20 L
aos 10.300 km → 300 / (10 + 20) = **10 km/L**.

- O primeiro ponto sozinho não dá consumo ("Primeiro tanque cheio" ou
  "Primeiro nível marcado").
- Parcial sem nível antes do primeiro ponto fica "Fora do cálculo"; depois
  dele, entra como "abastecido no meio".
- **Trecho curto**: com o marcador, quando o que foi gasto não passa da
  margem (ou a quilometragem não mudou). Não mostra km/L sozinho, mas entra
  na média do período.
- Carro **flex**: antes do primeiro abastecimento registrado não dá para
  saber se o tanque tinha gasolina ou etanol; a primeira marcação fica sem
  consumo até haver um tanque cheio.
- Ciclo com **mistura de combustíveis** (por exemplo, tanque com gasolina
  completado com etanol) ou em que a quilometragem não aumentou fica "Sem
  consumo" e não entra na média. O detalhe do abastecimento diz o motivo.
- A média de cada combustível é a distância total dividida pela quantidade
  total dos ciclos válidos (nunca a média simples dos km/L).
- No mesmo dia, a ordem é a da quilometragem. Incluir, editar ou apagar um
  abastecimento recalcula os ciclos afetados na hora.
- Sem ciclos válidos, a tela diz "Ainda não há consumo calculado" (não mostra
  zero).
- **Consumo por mês** (aba Combustível, até 12 meses): soma dos trechos que
  **começaram** no mês. Com a marcação no início de cada mês, o mês fecha
  certinho: do km e nível do dia 1 ao km e nível do dia 1 seguinte.

### 15.5 Etanol ou gasolina?

Só para veículo flex. O limite vem do consumo real do **seu** carro:
consumo do etanol ÷ consumo da gasolina (ex.: 7,9 ÷ 11,3 = **70%**). Não é
usado um percentual fixo.

- Compara com o último preço pago de cada combustível: se o etanol custou
  menos que o limite (ex.: R$ 4,29 ÷ R$ 6,25 = 69%), "Hoje, o etanol compensa".
- **Simular com os preços de hoje**: digite os preços da bomba e toque em
  **Comparar**. Nada é gravado.
- Sem a média dos dois combustíveis, a tela explica o que falta (é preciso
  ter pelo menos dois tanques cheios de cada um).

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

**0012** (tanque e marcador) só acrescenta colunas vazias e a tabela
`medicao_tanque`: não mexe em dado antigo e não tem o que conferir antes. Ela
não deixa voltar para a 0011 se já houver marcação, nível ou tamanho do
tanque gravado (seriam apagados).

### 15.7 Finanças

Cada abastecimento entra uma vez nas despesas, na categoria **Combustível**,
pela data dele. Tocar no lançamento abre o abastecimento.

## 16. Projetos de melhoria

Em **Mais → Projetos** (o menu mostra quantos estão em andamento).

### 16.1 Criar um projeto

Nome, descrição, categoria (exterior, interior, mecânica, som, outros),
orçamento (opcional) e previsão (opcional). Ele começa **Planejado** ou, se
já começou, **Em andamento**.

### 16.2 Situações

| Ação | De | Para |
|---|---|---|
| Iniciar projeto | planejado | em andamento |
| Marcar como concluído (pede a data; padrão: hoje) | planejado ou em andamento | concluído |
| Cancelar projeto | planejado ou em andamento | cancelado |
| Reabrir projeto | concluído ou cancelado | em andamento (a data de conclusão é apagada) |

- Os **gastos** só podem ser incluídos, editados ou apagados com o projeto
  planejado ou em andamento. Para mexer num concluído ou cancelado, reabra.
  Assim o total de um projeto encerrado não muda sem querer.
- **Cancelar não apaga os gastos**: o que foi gasto continua nas Finanças.
- **Apagar** o projeto apaga os gastos (saem das Finanças) e as fotos dele.
  Se o projeto só não vai mais acontecer, prefira cancelar.
- Reabrir mantém os gastos e as fotos, inclusive as de depois.

### 16.3 Orçamento

- Gasto = soma dos gastos do projeto (calculada pelo backend).
- Percentual = gasto ÷ orçamento, arredondado meio para cima ("84% do
  orçamento").
- "Restam R$ 700,00" (em andamento), "R$ 50,00 abaixo" (concluído) ou
  "R$ 150,00 acima do orçamento".
- Sem orçamento: não há percentual nem "restam". Orçamento R$ 0,00: não há
  percentual (sem divisão por zero) e todo gasto aparece como acima.

### 16.4 Fotos de antes e depois

- No detalhe, os quadros **Foto antes** / **Foto depois** abrem "Nova foto"
  já ligada ao projeto. Em "Nova foto", também dá para escolher **Ligar a um
  registro → Projeto** e o momento (Antes, Depois ou Outra).
- Pode haver várias fotos de cada; o cartão e o detalhe mostram a primeira (a
  mais antiga) e o detalhe lista as demais.
- A foto de depois pode ser enviada a qualquer momento ("Ao concluir" é só uma
  dica).
- Antes/depois exigem projeto do mesmo veículo. Na galeria, o filtro
  **Projetos** mostra essas fotos.

### 16.5 Finanças

Cada gasto do projeto entra uma vez nas Finanças, na categoria **Projetos**,
pela data dele, inclusive de projeto cancelado. Tocar no lançamento abre o
projeto.

### 16.6 Se a migration 0011 parar por causa de projetos ou fotos antigas

Ela lista, por exemplo:

- `projeto 3 (veículo 2, "Insulfilm") está concluído e sem data de conclusão`
  → no pgAdmin, informe a `data_conclusao` (a data real) ou mude o `status`;
- `projeto 4 (veículo 2, "Som") tem data de conclusão, mas está em_andamento`
  → apague a `data_conclusao` ou mude o `status` para `concluido`;
- `foto 9 (veículo 3) está ligada ao projeto 4, que é do veículo 2` → corrija
  o `projeto_id` da foto ou deixe vazio.

Nada foi alterado. Depois rode de novo `gerenciar.py migrar`.

## 17. Início, custo do veículo, histórico e administração

Esta parte não tem migration nova: usa as tabelas e views que já existem
(`vw_despesa`, `vw_historico`, `vw_usuario_resumo` e `leitura_km`).

### 17.1 Tela inicial

- **Atalhos**: Abastecer, Gasto, Manutenção e Problema abrem os formulários
  do veículo em uso.
- **Precisa de atenção**: manutenções atrasadas ou próximas, problemas em
  aberto, contas vencidas (ou que vencem hoje), tamanho do tanque que falta
  no cadastro e a marcação do km e do nível do mês (seção 15.3).
- **Nível do tanque**: o último nível registrado e, se o carro rodou depois, a estimativa de agora (seção 15.3).
- **Próximos gastos**: total e os três gastos futuros mais próximos (seção 14.3).
- **Gastos do mês**: o mesmo total da aba Finanças no mês atual (fuso de
  Brasília), em três grupos fixos como no PDF: Manutenção, Combustível e
  Outros (gastos avulsos + projetos). As categorias completas ficam em Finanças.
- **Consumo médio**: média dos tanques cheios do combustível do último
  abastecimento (se ele ainda não tiver média, o de média mais recente), com
  o período usado. Sem dois tanques cheios: "Dados insuficientes" e o motivo.
- **Custo por km**: o mesmo do "Meu veículo" (veja 17.2), com o período.

Nenhum indicador aparece como zero quando não há dados: a tela diz
"Dados insuficientes" e por quê.

### 17.2 Custo do veículo ("Meu veículo")

**Quanto esse carro já me custou** = valor da compra + todas as despesas
registradas (manutenções realizadas, abastecimentos, gastos pagos e gastos de
projetos, inclusive de projeto cancelado), cada valor contado uma vez.
Documentação = IPVA + licenciamento. Sem o valor da compra, o total mostra só
as despesas e avisa.

**Custo por quilômetro** (sem o valor da compra), com despesas e distância do
**mesmo período**:

| Situação | Início do período |
|---|---|
| Data e km da compra preenchidos e coerentes com as leituras | a compra |
| Compra sem data ou sem km, ou que contradiz as leituras | a primeira leitura de km com data (a tela avisa) |

- Fim do período: a leitura de km com data mais recente. Despesas lançadas
  depois dela entram quando você atualizar a quilometragem.
- Exemplo: compra em 15/03/2022 com 22.000 km, hoje 85.000 km → 63.000 km;
  R$ 47.700,00 de despesas no período → 47.700 ÷ 63.000 = R$ 0,76/km.
- Sem km rodado no período, ou sem leitura com data: "Dados insuficientes".
- Valores em centavos, arredondados meio para cima. Cada grupo é arredondado
  sozinho, por isso a soma dos grupos pode diferir 1 centavo do total; grupo
  abaixo de 1 centavo por km aparece como "menos de R$ 0,01".

### 17.3 Histórico

Mais → Histórico (ou "Histórico deste veículo" no Meu veículo).

- Mostra os lançamentos efetivados da `vw_historico` (manutenção realizada,
  abastecimento, gasto pago na data do pagamento, gasto de projeto) e os
  **problemas registrados, sem valor**: o custo de um problema é o da
  manutenção que o resolveu, que já aparece na lista. O total de cada mês soma
  só os lançamentos com valor.
- Agendadas e contas pendentes não aparecem (ainda não aconteceram).
- Filtros: Tudo, Manutenção, Combustível, Gastos, Projetos, Diagnósticos.
- Período: últimos 12 meses (o mês atual e os 11 anteriores, inteiros), um
  ano ou tudo. Cada linha abre o registro de origem.

### 17.4 Administração

Só aparece em Mais para quem tem perfil admin; os endereços `/api/admin/...`
respondem 403 para os demais (esconder o menu não é a proteção).

- **Usuários e veículos**: busca por nome ou e-mail, filtro Todos/Admin/Padrão,
  último acesso, contas desativadas em vermelho e todos os veículos (busca por
  placa, modelo ou dono). Tocar num veículo abre as telas normais dele, com o
  aviso "Você está vendo, como administrador, o veículo de outra conta".
- **Usuário**: mudar perfil e ativar/desativar. Desativar pede confirmação,
  tira a pessoa de todos os aparelhos na hora e cancela links de senha
  pendentes. Você não altera a **própria** conta por aqui: peça a outro admin.
  O banco continua impedindo ficar sem nenhum admin ativo.
- **Enviar link para nova senha**: o e-mail vai para a pessoa (no modo
  arquivo, um `.eml` em `backend\emails_dev\`). Você nunca vê nem define a
  senha. Para quem nunca entrou, o botão vira "Reenviar convite".
- **Botão "+" (criar conta)**: nome e e-mail; a conta nasce com perfil padrão
  e uma senha aleatória que ninguém conhece. A pessoa recebe um **convite**
  de uso único, válido por 7 dias (`CONVITE_DIAS` no `.env`), para criar a
  própria senha.

### 17.5 Como testar esta parte (no seu computador)

1. Reinicie o backend (pasta `backend`):
   `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`.
   Não há migration nova; `gerenciar.py estado` deve dizer "Nenhuma migration pendente".
2. Início: confira os gastos do mês, o consumo, o custo por km e os alertas
   com os seus dados reais.
3. Meu veículo: confira o custo total e o período do custo por km.
4. Mais → Histórico: troque filtros e período; abra um lançamento.
5. Como admin (Mais → Administração): busque usuários, abra um, envie o link,
   crie uma conta pelo "+" com um e-mail seu e abra o `.eml` gerado.

## 18. Usar pelo celular (rede local) e instalar como aplicativo

### 18.1 Como o celular chega ao sistema

```
Celular (Chrome) ──Wi-Fi──▶ Computador: Vite (porta 5173 ou 4173) ──▶ API em 127.0.0.1:8000 ──▶ PostgreSQL
                            aberto só na rede de casa                 só dentro do computador
```

- No celular, `localhost` é **o próprio celular**. Ele precisa do **IP do
  computador** na rede de casa, por exemplo `http://192.168.0.10:5173`.
- O celular fala só com o Vite. O Vite repassa `/api` para o backend, que
  continua escutando apenas em `127.0.0.1` (dentro do computador). **Não abra
  a porta 8000 (API) nem a 5432 (PostgreSQL) no firewall**: o celular nunca
  precisa delas, e o PostgreSQL nunca recebe conexão de fora.
- Computador e celular precisam estar **no mesmo Wi-Fi**. Fora de casa (dados
  móveis ou outro Wi-Fi), o celular não alcança o computador e o app mostra
  "Sem conexão com o servidor". Acessar de qualquer lugar exigiria hospedar o
  sistema num servidor com HTTPS, o que não faz parte deste projeto.

### 18.2 Descobrir o IP do computador

PowerShell, em qualquer pasta:

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.PrefixOrigin -eq "Dhcp" } | Select-Object InterfaceAlias, IPAddress
```

Use o `IPAddress` da linha `Wi-Fi` (ou `Ethernet`, se o computador estiver no
cabo), por exemplo `192.168.0.10`. Alternativa: `ipconfig` e procure
"Endereço IPv4". O roteador pode trocar esse número com o tempo; se o celular
parar de abrir, confira de novo (ou reserve o IP nas configurações do roteador).

### 18.3 Firewall do Windows (uma vez só)

1. A rede de casa precisa estar como **Privada**. Confira (PowerShell, qualquer pasta):

   ```powershell
   Get-NetConnectionProfile | Select-Object InterfaceAlias, NetworkCategory
   ```

   Se aparecer `Public` na rede de casa: Configurações → Rede e Internet →
   Wi-Fi → (nome da rede) → Tipo de perfil de rede → **Privada**.
2. Libere as portas do frontend **só na rede privada**. Abra o PowerShell
   **como administrador** (menu Iniciar → digite PowerShell → "Executar como
   administrador") e rode, em qualquer pasta:

   ```powershell
   New-NetFirewallRule -DisplayName "Meu Veiculo (rede de casa)" -Direction Inbound -Protocol TCP -LocalPort 5173,4173 -Action Allow -Profile Private
   ```

   Para desfazer: `Remove-NetFirewallRule -DisplayName "Meu Veiculo (rede de casa)"`.

Na primeira vez que o Vite abrir para a rede, o Windows também pode perguntar
se o **Node.js** pode se comunicar: marque só **Redes privadas**. Em Wi-Fi
público (shopping, faculdade), a regra não vale, e é isso que se quer: ninguém
de fora vê a tela de entrada.

### 18.4 Jeito 1: testar no celular durante o desenvolvimento (porta 5173)

1. Terminal 1, backend (pasta `meu-veiculo\backend`), igual ao de sempre:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
   ```

2. Terminal 2, frontend (pasta `meu-veiculo\frontend`):

   ```powershell
   npm run dev:celular
   ```

   Esperado: além de `Local: http://localhost:5173/`, aparece
   `Network: http://192.168.0.10:5173/  Wi-Fi` (com o seu IP). Se houver mais
   de uma linha `Network` (por exemplo `vEthernet (WSL...)`), use a do Wi-Fi.
3. No Chrome do celular, abra o endereço `Network`. A tela Entrar aparece.

Nesse modo as telas se atualizam sozinhas quando o código muda, mas o app
**não fica instalável** (veja 18.7).

### 18.5 Jeito 2: versão final, instalável (porta 4173)

É a versão gerada pelo build, com o manifesto e o service worker da PWA. Use
no dia a dia e na apresentação.

1. Terminal 1, backend (pasta `meu-veiculo\backend`): o mesmo comando de 18.4
   (pode ser sem `--reload`).
2. Terminal 2, frontend (pasta `meu-veiculo\frontend`):

   ```powershell
   npm run app:celular
   ```

   Ele roda o build e depois serve a pasta `dist`. Esperado:
   `Local: http://localhost:4173/` e `Network: http://192.168.0.10:4173/`.
3. No celular, abra `http://SEU-IP:4173`. No computador, `http://localhost:4173`.

Depois de mudar o código, pare (`Ctrl + C`) e rode `npm run app:celular` de
novo. Em uso real, o computador precisa ficar ligado com os dois terminais
abertos.

### 18.6 Links dos e-mails no celular

Os links de "redefinir senha" e de convite usam `URL_FRONTEND` do
`backend\.env`. Para abrirem também no celular, troque `localhost` pelo IP e
use a porta do jeito escolhido:

```
URL_FRONTEND=http://192.168.0.10:4173
```

Com HTTPS (seção 18.8), use `https://192.168.0.10:4173`. Reinicie o backend
depois de mudar. O computador também abre esse endereço.

### 18.7 HTTPS, instalação e câmera

| Recurso | `http://localhost` (computador) | `http://192.168.x.x` (celular na rede) |
|---|---|---|
| Entrar, cadastrar, consultar, enviar fotos | funciona | funciona |
| Câmera ("Tirar foto") | funciona | **funciona**: o app usa o campo de arquivo do navegador, que não exige HTTPS |
| Service worker (página "sem conexão") | funciona no jeito 2 | **não**: o navegador só permite em HTTPS ou localhost |
| Instalar como aplicativo (ícone, tela cheia) | funciona no jeito 2 | **não**: o menu do Chrome só cria um atalho, que abre como página comum |

O navegador trata `http://localhost` como seguro e `http://192.168.x.x` não.
Para testar a **instalação** no celular sem contratar nada, escolha uma das
alternativas abaixo (as duas no seu Android, só para teste):

**A. Cabo USB + encaminhamento de porta (recomendado).** O celular passa a
abrir `http://localhost:4173`, que é seguro.

1. No celular: Configurações → Sobre o telefone → toque 7 vezes em "Número
   da versão" para liberar as Opções do desenvolvedor; nelas, ligue
   **Depuração USB**.
2. Ligue o cabo e aceite "Permitir depuração USB" no celular.
3. No Chrome do **computador**, abra `chrome://inspect/#devices`, clique em
   **Port forwarding**, adicione `4173` → `localhost:4173`, marque "Enable
   port forwarding" e clique em Done.
4. Com `npm run app:celular` rodando, abra `http://localhost:4173` no Chrome do
   celular (o cabo precisa continuar ligado e a página `chrome://inspect`
   aberta no computador).

**B. Opção experimental do Chrome no celular.** Sem cabo, mas mexe numa
configuração de segurança do navegador:

1. No Chrome do celular, abra `chrome://flags/#unsafely-treat-insecure-origin-as-secure`.
2. Ative a opção e escreva `http://192.168.0.10:4173` (com o seu IP) no campo.
3. Toque em **Relaunch**. Depois dos testes, volte a opção para **Disabled**.

Com A ou B: Chrome do celular → menu ⋮ → **Instalar app** (ou "Adicionar à
tela inicial" → Instalar). O Meu Veículo ganha ícone próprio e abre em tela
cheia, sem a barra do navegador. O endereço continua sendo o do computador:
ele precisa estar ligado e no mesmo Wi-Fi.

**C. HTTPS na rede de casa (recomendado para o dia a dia).** Sem cabo e sem
configuração experimental: um certificado próprio criado com o mkcert e
instalado no celular. Passo a passo na seção 18.8.

### 18.8 HTTPS na rede de casa (certificado próprio com o mkcert)

As alternativas A e B da seção 18.7 servem para um teste rápido. Para usar o
app instalado no dia a dia, sem cabo e sem mexer em configurações
experimentais do Chrome, o caminho é **HTTPS de verdade** na rede de casa:
o endereço passa a ser `https://SEU-IP:4173`, com cadeado e sem aviso.

**Como funciona, em poucas palavras.** Um site HTTPS apresenta um
*certificado*, uma espécie de documento que diz "eu sou o 192.168.0.10". O
celular só aceita esse documento se ele for assinado por uma *autoridade
certificadora* em que ele confia. Na internet, essas autoridades são empresas.
Em casa, o programa gratuito **mkcert** cria uma autoridade **só sua**: você a
instala no computador e no celular, e ela assina o certificado do Meu Veículo.
Nada é contratado e nada sai da sua rede.

> **Cuidado com um arquivo:** o mkcert guarda a autoridade em dois arquivos,
> `rootCA.pem` (pode ir para o celular) e `rootCA-key.pem` (a **chave**, que
> **nunca** sai do computador). Quem tiver a chave consegue criar certificados
> falsos que o seu computador e o seu celular aceitariam para qualquer site.
> Não copie, não envie e não coloque no Git.

**Passo 1. Instalar o mkcert** (PowerShell comum, qualquer pasta):

```powershell
winget install FiloSottile.mkcert
```

Feche e abra o terminal de novo e confira com `mkcert -version`.

**Passo 2. Criar a sua autoridade e instalá-la no Windows** (uma vez só):

```powershell
mkcert -install
```

O Windows mostra um "Aviso de segurança" perguntando se você quer instalar um
certificado. É a sua autoridade: clique em **Sim**.

**Passo 3. Criar o certificado do Meu Veículo** (pasta `meu-veiculo\frontend`).
Descubra o IP do computador (seção 18.2) e troque `192.168.0.10` pelo seu:

```powershell
New-Item -ItemType Directory -Force certificados
mkcert -cert-file certificados\meu-veiculo.pem -key-file certificados\meu-veiculo-chave.pem localhost 127.0.0.1 192.168.0.10
```

Esperado: `The certificate is at "certificados\meu-veiculo.pem" and the key at
"certificados\meu-veiculo-chave.pem"`. A pasta `frontend\certificados` não vai
para o Git (está no `.gitignore`).

**Passo 4. Levar a autoridade para o celular.** Copie o `rootCA.pem` para a
Área de Trabalho com um nome que o Android reconhece:

```powershell
Copy-Item "$(mkcert -CAROOT)\rootCA.pem" "$HOME\Desktop\meu-veiculo-ca.crt"
```

Passe o `meu-veiculo-ca.crt` para o celular (cabo USB, Google Drive ou
e-mail para você mesma). No Android: **Configurações** → **Segurança e
privacidade** → **Mais configurações de segurança** → **Criptografia e
credenciais** → **Instalar um certificado** → **Certificado de CA** → **Instalar
assim mesmo** → escolha o arquivo. Os nomes mudam um pouco conforme a marca; se
não achar, procure "certificado" na busca das Configurações. O Android pode
pedir que o celular tenha bloqueio de tela (PIN ou padrão). Depois de
instalado, apague a cópia da Área de Trabalho e do Drive/e-mail (não é
secreta, mas não precisa ficar espalhada).

**Passo 5. Ajustar o `backend\.env`** e reiniciar o backend:

```
COOKIE_SEGURO=true
URL_FRONTEND=https://192.168.0.10:4173
```

`COOKIE_SEGURO=true` faz o cookie da sessão só trafegar criptografado. Com ele
ligado, os endereços `http://SEU-IP` (os jeitos 1 e 2 sem HTTPS) deixam de
manter o login; no computador, `http://localhost` continua funcionando no
Chrome, que trata `localhost` como seguro.

**Passo 6. Abrir com HTTPS.** Terminal 1, backend, como sempre (seção 18.4).
Terminal 2 (pasta `meu-veiculo\frontend`), escolha:

| Comando | Para quê | Endereço no celular |
|---|---|---|
| `npm run app:https` | versão final, instalável (troca o `app:celular`) | `https://192.168.0.10:4173` |
| `npm run dev:https` | desenvolvimento, atualiza ao salvar (troca o `dev:celular`) | `https://192.168.0.10:5173` |

Atenção ao **`https://`**: nesse modo, o endereço com `http://` não responde.
No celular, o Chrome deve mostrar o cadeado sem nenhum aviso. Instale pelo
menu ⋮ → **Instalar app**: agora o ícone abre em tela cheia e a página "Sem
conexão com o servidor" funciona, sem cabo.

**Se o IP do computador mudar** (o roteador pode trocar), repita só o passo 3
com o IP novo e ajuste o `URL_FRONTEND`. O celular não precisa de nada novo:
a autoridade continua a mesma. Para o IP não mudar, dá para reservar o IP do
computador nas configurações do roteador (cada modelo tem o seu jeito).

**Para desfazer tudo:** no computador, `mkcert -uninstall` e apague a pasta
`frontend\certificados`; no celular, **Criptografia e credenciais** →
**Credenciais do usuário** → toque na autoridade "mkcert" → **Remover**; no
`.env`, volte `COOKIE_SEGURO=false`.

**Situação de teste:** testei no seu computador, com um certificado de teste
criado por mim do mesmo jeito que o mkcert cria (autoridade própria +
certificado para `localhost`, `127.0.0.1` e o IP): `npm run app:https` abriu
por `https://localhost:4173` e `https://SEU-IP:4173`, entregou a página, o
service worker e o manifesto, e a API passou pelo proxy com `no-store`; sem os
arquivos do certificado, o comando para com a orientação desta seção. O
certificado de teste foi apagado depois. **Não testado por mim:** o mkcert em
si, a instalação da autoridade no seu Android e o cadeado no Chrome do celular
(dependem do seu aparelho). Observação: o **Avast** do seu computador examina
conexões HTTPS e por isso não deixou conferir a assinatura a partir do
computador; no celular ele não interfere.

### 18.9 O que o aplicativo instalado guarda no celular

- **Instalação** = ícone e abertura em tela cheia. **Cache** = cópia de
  arquivos no aparelho. **Offline** = funcionar sem servidor. São coisas
  diferentes, e o Meu Veículo **não funciona offline**: ver e salvar dados
  exige conexão com o computador.
- O service worker (`frontend\public\sw.js`) guarda só a página "Sem conexão
  com o servidor". **Nenhuma resposta de `/api` passa por ele**
  (há teste automático disso em `frontend\src\tests\pwa.test.ts`).
- Toda resposta da API sai com `Cache-Control: no-store` (o navegador não
  guarda). As fotos saem com `private, no-cache`: o navegador pode guardar a
  imagem, mas pergunta ao servidor a cada uso, e o servidor confere de novo
  quem está logado.
- Ao **Sair**, a API manda `Clear-Site-Data: "cache"`, que pede ao navegador
  para apagar o que guardou deste endereço. Os dados da conta ficam só na
  memória da página (nada em `localStorage`), então outra pessoa que entrar no
  mesmo celular não vê nada da conta anterior.
- Para remover: segure o ícone → Desinstalar (ou Chrome → Configurações →
  Configurações do site → o endereço → Limpar e redefinir).

### 18.10 Problemas comuns no celular

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| O celular não abre `http://SEU-IP:5173` (fica carregando e dá erro) | firewall, rede Pública, IP errado ou outro Wi-Fi | seção 18.3; confira o IP (18.2) e se o celular está no mesmo Wi-Fi (não nos dados móveis) |
| Abre no computador pelo IP, mas não no celular | firewall bloqueando conexões de fora | regra da seção 18.3 e rede Privada |
| `Network:` não aparece no terminal | usou `npm run dev` | use `npm run dev:celular` ou `npm run app:celular` |
| A tela abre, mas mostra "Não foi possível falar com o servidor" | backend parado | Terminal 1 (seção 18.4) |
| Link do e-mail abre `localhost` no celular e não carrega | `URL_FRONTEND` ainda com `localhost` | seção 18.6 |
| Não aparece "Instalar app", só um atalho comum | endereço `http://192.168...` não é seguro | alternativa A ou B da seção 18.7, com `npm run app:celular` |
| "Sem conexão com o servidor" ao abrir o app instalado | computador desligado, terminais fechados ou celular fora do Wi-Fi de casa | ligue o backend e o `npm run app:celular`; toque em "Tentar de novo" |
| Depois de atualizar o código, o celular mostra a versão antiga | a página antiga continua aberta | feche o app (ou a aba) e abra de novo |
| `Port 4173 is already in use` | outro `app:celular` ou `app:https` aberto | feche o outro terminal ou use `Ctrl + C` nele |
| `HTTPS: não encontrei meu-veiculo.pem...` ao rodar `app:https` ou `dev:https` | certificado ainda não criado ou na pasta errada | passo 3 da seção 18.8, na pasta `frontend` |
| Celular mostra "Sua conexão não é particular" em `https://...` | autoridade não instalada no celular, ou o IP mudou depois de criar o certificado | passos 3 e 4 da seção 18.8 |
| Com HTTPS, o endereço `http://...:4173` não abre | nesse modo só existe `https://` | digite `https://` |
| Entra, mas volta para a tela de login ao navegar | `COOKIE_SEGURO=true` com um endereço `http://SEU-IP` | use o endereço `https://` (ou volte `COOKIE_SEGURO=false`) |
| No computador, o Chrome avisa "Avast Untrusted Root" em `https://...` | o Avast não reconhece a autoridade (mkcert sem o `-install`) | rode `mkcert -install` de novo e reabra o Chrome; ou use `http://localhost:5173` no computador |

## 19. O que foi testado e o que depende do seu ambiente

Situação em 02/10/2026, fim da etapa 11. "Testado" quer dizer que o teste foi
executado e passou; nada aqui foi marcado só porque o código existe.

### 19.1 Testes automáticos (executados)

| Suíte | Comando (pasta) | Resultado |
|---|---|---|
| Backend, no PostgreSQL de teste (domains, views e triggers reais; nada de SQLite) | `.\.venv\Scripts\python.exe -m pytest` (`backend`) | 780 passaram, 0 falharam |
| Frontend (telas, cálculos de tela, PWA) | `npm test` (`frontend`) | 218 passaram, 0 falharam |
| Tipos do TypeScript | `npm run typecheck` (`frontend`) | sem erros |
| Versão final | `npm run build` (`frontend`) | gerada (só o aviso de tamanho, seção 7) |

### 19.2 Critérios de aceite do pedido e onde estão os testes

Todos os arquivos ficam em `backend\tests\`.

| Critério | Arquivos |
|---|---|
| E-mail igual em maiúsculas/minúsculas, tentar escolher admin no cadastro, conta desativada com sessão antiga | `test_auth_api.py`, `test_permissoes.py`, `test_migracao_0002.py` |
| Dois usuários padrão e um admin; acessar ou alterar veículo, registro, anotação, item e foto de outra pessoa, inclusive por ID direto | `test_permissoes.py` e os `test_*_api.py` de cada módulo |
| Vincular registros de veículos diferentes, inclusive do mesmo dono | `test_manutencoes_api.py`, `test_diagnosticos_api.py`, `test_fotos_api.py`, `test_projetos_api.py`, `test_migracao_0004.py`, `test_migracao_0006.py`, `test_migracao_0011.py` |
| Link de recuperação válido, expirado, reutilizado e usado ao mesmo tempo; troca de senha encerra sessões | `test_recuperacao_senha.py`, `test_auth_api.py`, `test_sessao.py` |
| Km antigo não reduz o atual; agendada não aumenta; mudança só de status para realizada; correção e recálculo | `test_quilometragem_api.py`, `test_manutencoes_api.py`, `test_migracao_0003.py` |
| Plano sem manutenção anterior, prazos por km e por tempo, o que vence primeiro, faixas de 1.000 km/30 dias | `test_manutencoes_api.py`, `test_migracao_0004.py` |
| Resolver diagnóstico com manutenção e falha forçada desfazendo as duas | `test_diagnosticos_api.py` |
| Totais sem duplicar, pago/pendente, mês do pagamento, arredondamento, gastos de projeto cancelado | `test_gastos_api.py`, `test_projetos_api.py`, `test_historico_api.py`, `test_custo_e_painel_api.py` |
| Consumo: dois cheios, parciais, dados insuficientes, históricos, mistura de combustível, etanol × gasolina sem percentual fixo, marcador do tanque | `test_consumo.py`, `test_abastecimentos_api.py`, `test_tanque_api.py` |
| Custo por km do mesmo período, sem dados da compra e distância zero | `test_custo_e_painel_api.py` |
| Foto com formato ou tamanho inválido, acesso indevido, troca de capa, vínculo do mesmo veículo | `test_fotos_api.py` |
| Orçamento ausente, zero e excedido; veículo inativo preservando histórico; último admin protegido | `test_projetos_api.py`, `test_veiculos_api.py`, `test_admin_api.py` |
| Migrations: banco vazio, banco existente, dados antigos incompatíveis listados sem alterar nada | `test_migracoes.py`, `test_esquema_original.py`, `test_migracao_00*.py` |
| Camadas do backend e entities iguais ao banco | `test_arquitetura.py`, `test_entities.py` |
| Nada da conta guardado no navegador (no-store, fotos revalidadas, limpeza ao sair) | `test_cache_navegador.py`, `test_fotos_api.py`; PWA em `frontend\src\tests\pwa.test.ts` |

### 19.3 Testado no navegador (Chrome do computador, automatizado)

Em cada etapa, o fluxo principal foi percorrido no Chrome com o backend
ligado ao banco de **teste** (registro em `docs\progresso.md`). Na etapa 10,
com a versão final (build + preview):

- Em `http://localhost`: service worker registrado, manifesto lido ("Meu
  Veículo", tela cheia), Cache Storage só com `offline.html`; troca de versão
  do service worker apagando o cache antigo.
- Conta criada, veículo cadastrado, Início exibido; **Sair** pela tela:
  volta para Entrar, a sessão deixa de valer (401), `localStorage` e
  `sessionStorage` vazios, nada de `/api` no Cache Storage; o servidor manda
  `Clear-Site-Data: "cache"` e `Cache-Control: no-store`.
- Servidor desligado: a tela mostra "Sem conexão com o servidor" com o ícone.
- Pelo IP da rede (`http://192.168.1.40`, no próprio computador): o app abre,
  não há service worker (contexto não seguro, como esperado), cadastro e
  sessão funcionam, a segunda conta não vê o veículo da primeira (404), e o
  backend recebeu o IP de quem acessou pelo proxy (usado no limite de
  tentativas).
- Log do backend sem erro 5xx e sem senha ou token.

### 19.4 Depende do seu ambiente (não testado por mim)

| Item | Por quê | Como validar |
|---|---|---|
| Abrir no **celular** pela rede de casa | depende do seu Wi-Fi, do firewall e do Android | seções 18.2 a 18.5 |
| Regra do firewall e rede Privada | exige PowerShell como administrador | seção 18.3 |
| **Instalar** o app no Android | exige contexto seguro no celular (cabo USB ou opção do Chrome) | seção 18.7 |
| **Câmera** do celular ("Tirar foto") e fotos HEIC de iPhone | depende do aparelho; a conversão de HEIC está testada no backend | enviar uma foto pela câmera e conferir a galeria |
| Envio real de e-mail pelo Gmail | depende da sua conta e da "senha de app"; o envio por SMTP está testado com servidor falso | seção 10.2 (`gerenciar.py testar-email`) |
| Link do e-mail aberto no celular | depende de `URL_FRONTEND` com o IP | seção 18.6 |
| HTTPS com certificado próprio (mkcert) | configurado e testado no computador com certificado de teste; mkcert e celular dependem de você | seção 18.8 |
| iPhone/Safari | fora do aparelho escolhido (Android + Chrome) | compatibilidade não validada |
| Uso fora de casa | exigiria hospedagem com HTTPS, fora do escopo | — |

## 20. Dados de exemplo para apresentação

Para apresentar o sistema (TCC) sem mostrar nem misturar os seus dados reais,
existe uma carga **opcional** de dados de exemplo. Ela grava só num banco
próprio, `meu_veiculo_demo` (`DB_NOME_DEMO`), e nunca no de desenvolvimento
(há uma trava: o nome precisa terminar em `_demo`). As migrations não criam
dados de exemplo, e o sistema continua funcionando com banco vazio.

### 20.1 O que é criado

- **Paula Demonstração** (`paula@exemplo.com.br`, administradora): um Honda
  Civic com uns 8 meses de histórico, terminando nesta semana: abastecimentos
  de gasolina e etanol (com troca de combustível e nível do marcador), planos de
  manutenção (um próximo do limite), manutenções com peças e mão de obra e uma
  agendada, um problema resolvido por manutenção, um em aberto e um descartado,
  gastos pagos, uma conta vencida e uma a vencer, projetos (concluído, acima do
  orçamento e planejado) e fotos (capa, nota fiscal, problema, antes e depois);
  e uma moto com alguns abastecimentos.
- **Rafael Demonstração** (`rafael@exemplo.com.br`, perfil padrão): um Fiat
  Argo, para a tela de Administração ter mais de uma conta.
- Senha das duas contas: `meu veiculo de exemplo`. Não é segredo: está no
  arquivo `backend\demonstracao\carga_exemplo.py` e serve só para a demonstração.

As datas são calculadas a partir do dia em que você carrega: o Início mostra
gastos do mês, alertas e indicadores de verdade. Os dados entram pela própria
API, com as mesmas regras das telas.

### 20.2 Preparar (uma vez só)

Pasta `meu-veiculo\backend`:

1. Criar o banco de demonstração. O comando pede a senha do `postgres` e não
   apaga nada nos bancos que já existem:

   ```powershell
   .\.venv\Scripts\python.exe gerenciar.py criar-bancos
   ```

   Esperado: `Banco 'meu_veiculo_demo' criado.` (os outros: "já existia: nada foi apagado").
2. Carregar os dados (aplica as migrations no banco de demonstração e grava os exemplos):

   ```powershell
   .\.venv\Scripts\python.exe gerenciar.py carregar-exemplo
   ```

   Esperado: `Dados de exemplo gravados no banco 'meu_veiculo_demo': 3 veículos, ... e 5 fotos.`

O comando usa bibliotecas de desenvolvimento (`requirements-dev.txt`), que
você já instalou na seção 4.2.

### 20.3 Abrir o sistema com os dados de exemplo

**Terminal 1, backend** (pasta `meu-veiculo\backend`), num terminal **novo**:

```powershell
$env:DB_NOME = "meu_veiculo_demo"
.\.venv\Scripts\python.exe -m uvicorn app.main:app
```

**Terminal 2, frontend** (pasta `meu-veiculo\frontend`): `npm run dev` ou
`npm run app:celular` (seção 18), como sempre. Entre com uma das contas de 20.1.

`$env:DB_NOME` vale **só para aquele terminal**: enquanto ele estiver aberto,
o backend usa o banco de demonstração. Para voltar aos seus dados, pare o
backend (`Ctrl + C`), **feche esse terminal** e inicie o backend num terminal
novo, sem a primeira linha. Não rode `gerenciar.py migrar` ou `backup` nesse
terminal pensando que é o banco de verdade.

### 20.4 Atualizar as datas antes da apresentação

Para começar de novo, com o histórico terminando no dia de hoje (apaga **só**
o banco de demonstração; pare o backend de demonstração antes):

```powershell
.\.venv\Scripts\python.exe gerenciar.py carregar-exemplo --recomecar
```

Sem `--recomecar`, o comando se recusa a carregar num banco de demonstração que
já tem contas.
