# Meu Veículo — resumo técnico para o texto do TCC

Material de apoio para escrever os capítulos de desenvolvimento, arquitetura,
testes e resultados. Os textos estão em linguagem de monografia e podem ser
adaptados. Os números foram medidos em 02/10/2026 (seção 7). As justificativas
completas, com data, estão em `docs/decisoes.md`.

---

## 1. Objetivo e escopo

O Meu Veículo é uma aplicação web instalável (PWA) para cada usuário
acompanhar os próprios veículos: quilometragem, abastecimentos e consumo,
manutenções (realizadas, agendadas e planos recorrentes), diagnósticos de
problemas, gastos, projetos de melhoria e fotos. O sistema calcula
indicadores como consumo médio, custo por quilômetro, custo total do veículo,
nível estimado do tanque e manutenções próximas ou atrasadas, e reúne tudo
numa tela inicial e num histórico.

Requisitos não funcionais que guiaram o projeto:

- uso no computador e no celular (Android/Chrome) com um único código;
- dados isolados por usuário, com perfil de administrador;
- valores monetários exatos e datas sem erro de fuso horário;
- evolução do banco de dados sem perda de dados existentes;
- funcionamento com banco vazio (sem depender de dados de exemplo).

## 2. Tecnologias

| Camada | Tecnologia | Versão |
|---|---|---|
| Interface | React + TypeScript, empacotado com Vite | React 19.3, TypeScript 7.0, Vite 8.3 |
| Navegação | React Router | 8.4 |
| API | FastAPI (Python) | FastAPI 0.141, Python 3.13 |
| Acesso ao banco | SQLAlchemy + psycopg | SQLAlchemy 2.1, psycopg 3.3 |
| Migrations | Alembic, com SQL escrito à mão | Alembic 1.20 |
| Banco de dados | PostgreSQL | 16 |
| Senhas | Argon2id (argon2-cffi) | 25.1 |
| Imagens | Pillow (+ pillow-heif para fotos HEIC) | 12.3 |
| Testes | pytest (backend) e Vitest + Testing Library (frontend) | pytest 9.1, Vitest 5.0 |

**Por que PWA e não aplicativo nativo.** Uma aplicação web responsiva e
instalável atende computador e celular com o mesmo código, dispensa a
publicação em lojas e permite instalar o app com ícone e tela cheia. As
alternativas avaliadas (React Native e Flutter) exigiriam um segundo código
ou outra linguagem, sem ganho para as funções do sistema, que não dependem de
recursos exclusivos do celular: a câmera é acessada pelo campo de arquivo do
navegador.

## 3. Arquitetura

### 3.1 Visão geral

```
Navegador (computador ou celular)
        │  HTTPS na rede local (opcional) — só /api/...
        ▼
Frontend React (Vite) ── proxy /api ──► Backend FastAPI (127.0.0.1:8000)
                                              │
                                              ▼
                                        PostgreSQL 16
```

O navegador conhece apenas o endereço do frontend; as chamadas `/api` são
repassadas ao backend, que escuta só no próprio computador. **Somente o
backend acessa o banco de dados**: nenhuma credencial chega ao navegador.

### 3.2 Backend em camadas

Cada requisição percorre camadas com responsabilidades separadas:

```
Route → Controller → Service → Repository → banco (sessão/transação) → PostgreSQL
```

| Camada | Responsabilidade |
|---|---|
| Route | declara o endpoint (método, caminho, formatos) |
| Controller | traduz HTTP: lê a requisição, monta a resposta, converte erros de negócio em códigos HTTP |
| Service | regras de negócio e transações; não conhece FastAPI nem SQL |
| Repository | todo o SQL e o acesso às tabelas |
| Entities / Schemas | classes das tabelas (SQLAlchemy) e formatos JSON de entrada e saída (Pydantic) |
| Banco | conexão, sessão, unidade de trabalho, migrations e backup |

A separação é verificada automaticamente: um teste
(`tests/test_arquitetura.py`) lê os imports de cada arquivo e falha se uma
camada usar outra que não deveria (por exemplo, um service importando
FastAPI). Outro teste (`tests/test_entities.py`) compara as classes com a
estrutura real do banco.

### 3.3 Frontend

Organizado como projeto React (páginas, componentes, contextos, hooks,
serviços e tipos). Um único módulo (`services/apiCliente.ts`) faz todas as
chamadas à API. O estado da conta fica só em memória, nada em
`localStorage`. O service worker guarda apenas a página "sem conexão" e
nunca as respostas da API.

## 4. Banco de dados

O ponto de partida foi o script SQL recebido
(`database/original/meu_veiculo_banco.sql`: 11 tabelas, 4 views, 3 triggers
e 2 domains), que **nunca foi editado**: a primeira migration o executa e
confere sua integridade por hash SHA-256. Cada ajuste posterior entrou como
migration numerada:

| Migration | Conteúdo |
|---|---|
| 0001 | SQL original, conferido por SHA-256 |
| 0002 | autenticação: sessões, recuperação de senha, tentativas de acesso, e-mail normalizado |
| 0003 | veículos e histórico de leituras de quilometragem |
| 0004 | manutenções e planos recorrentes |
| 0005 | itens da manutenção (peças e mão de obra) |
| 0006 | diagnósticos |
| 0007 | gastos e finanças |
| 0008 | abastecimentos |
| 0009 | tipo do combustível e valor do cupom |
| 0010 | tipos por combustível |
| 0011 | projetos de melhoria |
| 0012 | tamanho do tanque e nível do marcador |
| 0013 | imagens das fotos dentro do PostgreSQL |
| 0014 | confirmação do e-mail ao criar a conta |

Estado atual: 18 tabelas, 5 views e 14 triggers.

**Evolução sem perda de dados.** Antes de criar uma restrição nova, a
migration procura registros antigos incompatíveis e, se houver, para e os
lista, sem apagar, unir ou inventar valores. Há procedimentos separados para
instalar num banco vazio e para adotar um banco criado antes com o script
original, e o comando de migração faz backup (`pg_dump`) antes de alterar um
banco existente.

**Integridade no próprio banco.** Além das verificações na API, o banco
garante regras que não podem ser violadas nem por acesso direto (por
exemplo, pelo pgAdmin): registros vinculados pertencem ao mesmo veículo, o
último administrador ativo não pode ser desativado e a quilometragem atual do
veículo é recalculada a partir das leituras.

## 5. Regras de negócio relevantes

- **Dinheiro:** sempre `Decimal`, com arredondamento meio para cima em
  centavos; os totais são calculados no servidor, nunca aceitos do
  navegador.
- **Datas:** campos de data sem conversão de fuso; regras de calendário
  (hoje, mês, vencimento) no fuso `America/Sao_Paulo`.
- **Indicador desconhecido não é zero:** sem dados suficientes, o sistema
  exibe "dados insuficientes" e o motivo.
- **Consumo:** calculado entre dois pontos em que se sabe quanto falta para
  encher o tanque (tanque cheio, nível do marcador antes de abastecer ou
  marcação do tanque): km rodados divididos pelos litros do trecho.
- **Etanol ou gasolina:** o limite de vantagem do etanol vem da razão entre
  os consumos reais do próprio veículo com cada combustível, e não do valor
  fixo de 70%.
- **Abastecimento:** basta informar dois de três valores (litros, preço,
  total) e o sistema calcula o terceiro; litros acima do que cabe no tanque
  são recusados.
- **Manutenção:** planos por km, por meses ou pelos dois; cada obrigação
  aparece uma vez na lista de pendentes (atrasada, próxima, em dia ou dados
  insuficientes).
- **Finanças:** gasto pago entra no mês do pagamento; gastos pendentes e
  manutenções agendadas ficam fora dos totais e aparecem em "vencidas" e
  "gastos futuros".
- **Quilometragem:** nunca é alterada diretamente; toda mudança é uma
  leitura registrada ou corrigida, e o banco recalcula o valor atual.

## 6. Segurança

| Tema | Solução adotada |
|---|---|
| Senhas | Argon2id (RFC 9106); só o hash é guardado; política de 8 a 128 caracteres, recusando senhas muito comuns |
| Confirmação do e-mail | a conta criada pela tela só entra depois de abrir o link enviado ao e-mail (uso único, 48 horas, só o hash guardado); contas anteriores à regra continuam entrando |
| Sessão | token aleatório em cookie `HttpOnly`, `SameSite=Lax`, restrito a `/api` (e `Secure` com HTTPS); o banco guarda só o hash do token |
| Requisições forjadas (CSRF) | toda gravação exige o cabeçalho `X-MV-Requisicao: 1`, que outro site não consegue enviar |
| Permissões | conferidas no servidor em toda leitura e gravação: dono do veículo ou administrador, senão "não encontrado" (não revela que o registro existe) |
| Login | limite de 5 erros por e-mail ou 20 por endereço de rede em 15 minutos |
| Recuperação de senha | link de uso único, válido por 60 minutos, só o hash guardado; troca da senha e consumo do link na mesma transação; todas as sessões encerradas depois |
| Privacidade no aparelho | respostas da API com `Cache-Control: no-store`; ao sair, o navegador é instruído a apagar o cache do endereço |
| Segredos | só no arquivo `.env` do backend, fora do controle de versão; nada de senha, token ou hash em logs ou respostas |
| Fotos | tipo verificado pelo conteúdo, imagem regravada (remove metadados como localização), tamanho limitado, entregue só a quem tem acesso ao veículo |

**Decisão que alterou o requisito original.** O pedido inicial previa que a
recuperação de senha não revelasse se um e-mail está cadastrado e que tivesse
limite de tentativas. Depois do uso do sistema, a autora optou por informar
"E-mail não existente, digite novamente" e remover o limite nessa tela,
priorizando quem digita o e-mail errado. Os riscos aceitos (descobrir quais
e-mails têm conta; muitos pedidos para o mesmo e-mail) estão registrados em
`docs/decisoes.md`. O login manteve a proteção contra tentativas.

## 7. Testes e números do projeto

Todos os testes do backend rodam num **PostgreSQL de teste real**, separado do
banco de desenvolvimento. O SQLite foi descartado porque não comprova
domains, views e triggers do PostgreSQL.

| Suíte | Quantidade | Resultado (02/10/2026) |
|---|---|---|
| Backend (pytest, API e banco reais) | 796 testes | todos passaram |
| Frontend (Vitest + Testing Library) | 224 testes | todos passaram |
| Tipos (TypeScript) | — | sem erros |

O que os testes cobrem, por exemplo: cada migration aplicada em banco com
dados antigos incompatíveis; isolamento entre usuários em todas as rotas;
consumo de link de recuperação por duas requisições simultâneas; totais
financeiros sem duplicação; consumo e nível do tanque; envio de e-mail por
SMTP com um servidor de teste; arquitetura em camadas.

| Medida | Valor |
|---|---|
| Endpoints da API | 95 |
| Telas (páginas React) | 35 |
| Migrations | 14 |
| Decisões técnicas registradas | mais de 100 (`docs/decisoes.md`) |
| Linhas de código do backend (sem testes) | cerca de 11.600 |
| Linhas de código do frontend (sem testes, sem CSS) | cerca de 12.300 |
| Linhas de testes (backend + frontend) | cerca de 13.000 |
| Linhas das migrations | cerca de 1.800 |

Além dos testes automáticos, cada etapa foi validada pela autora com os
próprios dados, no computador e num celular Android pela rede local
(registro em `docs/progresso.md`).
<!-- Paula: se você testou o envio pelo Gmail e/ou o HTTPS com o mkcert,
acrescente aqui (ex.: "incluindo o envio real de e-mail pelo Gmail"). -->


## 8. Limitações e trabalhos futuros

- **Sem funcionamento offline:** consultar e registrar exige conexão com o
  servidor; o app instalado mostra uma página de "sem conexão".
- **Acesso só na rede local:** usar fora de casa exigiria hospedagem com
  HTTPS e domínio próprio.
- **iPhone/Safari** não foi validado (o aparelho de referência é Android).
- **Backup automático** ainda é manual (`gerenciar.py backup`); pode ser
  agendado no Agendador de Tarefas do Windows.
- **Recuperação de senha** sem limite de tentativas, por escolha da autora
  (seção 6).
- Possíveis evoluções: lembretes por e-mail de manutenção e vencimentos,
  exportação de relatórios (PDF/planilha), importação de notas fiscais e
  gráficos de evolução de gastos e consumo.

## 9. Processo de desenvolvimento

O desenvolvimento foi dividido em etapas incrementais (0 a 12), cada uma com
código, testes executados e validação da autora antes da seguinte; o quadro
está em `docs/progresso.md`. As decisões técnicas foram registradas com data,
motivo e alternativas em `docs/decisoes.md`, e o `README.md` documenta
instalação, uso, solução de problemas e o que foi ou não testado em cada
ambiente.
