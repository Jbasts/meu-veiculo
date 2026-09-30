# Meu Veículo — instruções para o Claude Code

Projeto de TCC da Paula: aplicação para cada usuário acompanhar seus veículos, gastos, abastecimentos, manutenções, diagnósticos (problemas), projetos de melhoria e fotos. Depois do TCC ela pretende usar o sistema no dia a dia, então precisa conseguir executar, entender e continuar o projeto sozinha.

## Fontes da verdade (leia antes de qualquer etapa)

- `docs/requisitos.md`: pedido completo (escopo funcional, revisão do banco, arquitetura, entregas por etapa, testes e critérios de aceite). Prevalece sobre números ilustrativos do PDF e sobre comportamentos incorretos do SQL.
- `docs/telas-mobile.pdf`: referência visual e de navegação. Nomes, veículos, datas e valores das telas são exemplos; os dados reais vêm do banco. Se não conseguir ler o PDF, avise antes de implementar o que depende dele.
- `database/original/meu_veiculo_banco.sql`: estrutura inicial do PostgreSQL. Não edite este arquivo. Toda mudança entra como migration nova e versionada.
- `docs/observacoes-anexos.md`: pontos extras notados nos anexos, a confirmar na etapa 0.
- `docs/progresso.md`: quadro das etapas. Atualize ao fim de cada etapa.
- `docs/decisoes.md`: registre cada decisão técnica relevante com o motivo.

## Como trabalhar com a Paula

- Escreva em português do Brasil, passo a passo, com exemplos concretos. Explique o porquê das decisões em linguagem acessível.
- Trabalhe uma etapa por vez, na ordem de `docs/progresso.md`. Ao terminar uma etapa, pare e espere ela testar e responder antes de começar a próxima, a menos que ela peça para seguir.
- A etapa 0 é exatamente a "primeira resposta" descrita em `docs/requisitos.md` (análise dos anexos, inconsistências do banco, comparação web/PWA × app nativo ou multiplataforma, stack recomendada e perguntas indispensáveis). Não escreva código na etapa 0.
- Preferência que ela já declarou: React no frontend, FastAPI (Python) no backend e PostgreSQL. Faça a comparação pedida mesmo assim e leve essa preferência em conta na recomendação.
- Ela usa Windows com VS Code. Mostre os comandos em PowerShell e diga em qual pasta cada um deve ser executado. Se algo exigir CMD, explique a diferença. Lembre que no celular `localhost` não é o computador dela.
- Quando ela relatar um erro, analise a mensagem, corrija no arquivo correspondente e preserve o que já funciona. Não recomece nem reestruture o projeto sem necessidade.

## Honestidade sobre testes (obrigatório)

- Sempre separe três coisas: código escrito; teste que você executou e viu passar; validação que ainda depende do ambiente dela (celular, câmera, e-mail real, HTTPS, rede local).
- Só afirme que algo passou se você executou e viu o resultado. Mostre o comando e um resumo da saída (quantos passaram e falharam).
- Testes de banco e de integração usam PostgreSQL real, num banco de teste separado do banco de desenvolvimento. SQLite não serve: não comprova domains, views e triggers deste SQL.
- Ao fim de cada etapa, rode também a suíte das etapas anteriores para pegar regressões.

## Regras que nunca podem ser quebradas

- Só o backend acessa o PostgreSQL. O celular fala com a API, nunca com o banco.
- Nenhum segredo no frontend nem em variáveis públicas (por exemplo, `VITE_*`). Nada de senha, token ou hash em logs ou respostas da API.
- Permissões verificadas no backend em toda leitura e escrita, inclusive listagens, indicadores, anotações, itens de projeto e conteúdo das fotos. Não confie em `usuario_id`, `veiculo_id`, perfil ou IDs relacionados vindos do cliente: confira a propriedade e se os registros vinculados são do mesmo veículo (vale também para admin).
- Dinheiro com `Decimal` e arredondamento definido e documentado, nunca `float`. O backend calcula os totais; não confie em totais enviados pelo frontend.
- Campos `DATE` sem conversão acidental de fuso; regras de calendário em `America/Sao_Paulo`.
- Indicador desconhecido não é zero. Mostre "dados insuficientes" e o motivo.
- Não altere migrations já aplicadas; crie uma nova. Separe instalação em banco vazio de atualização de banco existente. Antes de uma restrição nova, detecte dados antigos incompatíveis e mostre-os; não apague, não una e não invente datas ou valores.
- Dados demonstrativos só numa carga opcional de desenvolvimento, desligada por padrão. O sistema precisa funcionar com banco vazio.
- Não exiba na conversa o conteúdo de arquivos `.env`. Para criar um `.env`, copie o `.env.example` (sem segredos reais) e peça para a Paula preencher as senhas.
- Não faça `git commit`, `git push` nem apague arquivos fora do escopo da etapa sem a Paula autorizar. Ao fim de cada etapa, sugira a mensagem de commit.

## Estrutura (confirmada na etapa 1)

```
meu-veiculo/
├── CLAUDE.md
├── README.md                 # guia completo, atualizado a cada etapa
├── backend/
│   ├── gerenciar.py          # comandos do banco (criar-bancos, estado, migrar, adotar, backup)
│   ├── migrations/versions/  # Alembic; 0001 = SQL original (conferido por SHA-256)
│   ├── tests/                # pytest no PostgreSQL de teste
│   └── app/
│       ├── main.py, config.py, dependencias.py
│       ├── routes/  controllers/  services/  repositories/
│       ├── entities/  schemas/  banco/
├── frontend/src/             # pages, components, contexts, hooks, services, types, utils, styles, tests
├── database/original/        # SQL recebido (somente leitura)
└── docs/                     # requisitos, telas, progresso, decisões
```

## Arquitetura do backend (obrigatória)

Fluxo: Route → Controller → Service → Repository → `banco/` → PostgreSQL. Detalhes e roteiro para endpoints novos no README (seção 3).

- routes: só endpoints; controllers: requisição/resposta HTTP e tradução de erros; services: regras e transações (`UnidadeDeTrabalho`), sem FastAPI nem SQLAlchemy; repositories: todo o SQL; entities: classes SQLAlchemy das tabelas existentes (nunca `create_all`); schemas: JSON de entrada/saída (Pydantic); banco: conexão, sessão, migrations, backup.
- `tests/test_arquitetura.py` impede imports que furem as camadas; `tests/test_entities.py` confere entities com o banco.
- Rotas que exigem login usam `SessaoAtualDep`; só admin, `AdminDep` (`app/dependencias.py`). Toda gravação exige o cabeçalho `X-MV-Requisicao: 1` (o `apiCliente.ts` já envia). Erros de regra: classes de `services/erros.py`.
- Frontend segue organização React (pages, components, services, types), não as camadas do backend.

## Comandos do projeto

PowerShell. No PowerShell, o `npm` exige `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (ou use `npm.cmd`).

- Preparar backend (pasta `backend`): `python -m venv .venv` e `.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`
- Criar usuário e bancos (pasta `backend`, pede a senha do postgres): `.\.venv\Scripts\python.exe gerenciar.py criar-bancos`
- Estado / aplicar migrations (pasta `backend`): `.\.venv\Scripts\python.exe gerenciar.py estado` / `... gerenciar.py migrar` (`--teste` para o banco de teste)
- Banco já existente criado com o SQL original (pasta `backend`): `... gerenciar.py backup` e `... gerenciar.py adotar-banco-existente`
- Primeiro administrador (pasta `backend`, conta já criada pela tela): `.\.venv\Scripts\python.exe gerenciar.py promover-admin EMAIL`
- E-mails de desenvolvimento (modo arquivo): arquivos `.eml` em `backend\emails_dev\` (fora do Git)
- Iniciar backend (pasta `backend`): `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload` → http://127.0.0.1:8000/docs
- Preparar frontend (pasta `frontend`): `npm ci`
- Iniciar frontend (pasta `frontend`): `npm run dev` → http://localhost:5173
- Testes backend (pasta `backend`): `.\.venv\Scripts\python.exe -m pytest`
- Testes frontend (pasta `frontend`): `npm test` e `npm run typecheck`
