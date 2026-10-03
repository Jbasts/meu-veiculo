# Roteiro da apresentação do Meu Veículo

Roteiro para mostrar o sistema à banca do TCC com os **dados de exemplo**,
sem expor os seus dados reais. Tempo previsto da demonstração: **cerca de 15
minutos**, em blocos. Se tiver menos tempo, os blocos marcados como
*(opcional)* podem sair sem quebrar a história.

As telas e os valores citados aqui vêm do que a carga de exemplo grava
(`backend\demonstracao\carga_exemplo.py`). Como as datas são calculadas a
partir do dia da carga, alguns números mudam um pouco (dias até a revisão,
nível estimado do tanque). **Ensaie pelo menos uma vez com a carga feita no
dia** para conferir os valores que vai falar.

Os valores citados abaixo foram conferidos no navegador em 03/10/2026, com a
carga de exemplo feita nesse dia (num banco de teste).

---

## 1. Preparação

### 1.1 Uma vez só (dias antes)

Pasta `meu-veiculo\backend`:

1. Criar o banco de demonstração (pede a senha do `postgres`; não apaga nada
   nos bancos que já existem):

   ```powershell
   .\.venv\Scripts\python.exe gerenciar.py criar-bancos
   ```

   Esperado: `Banco 'meu_veiculo_demo' criado.`
2. Carregar os dados:

   ```powershell
   .\.venv\Scripts\python.exe gerenciar.py carregar-exemplo
   ```

3. Ensaiar o roteiro inteiro (seção 2) com cronômetro.

### 1.2 No dia (ou na véspera)

1. Recarregar para o histórico terminar no dia da apresentação
   (pasta `backend`; apaga **só** o banco de demonstração):

   ```powershell
   .\.venv\Scripts\python.exe gerenciar.py carregar-exemplo --recomecar
   ```

2. **Terminal 1, backend de demonstração** (pasta `backend`, terminal novo):

   ```powershell
   $env:DB_NOME = "meu_veiculo_demo"
   .\.venv\Scripts\python.exe -m uvicorn app.main:app
   ```

   Sem `--reload`: na apresentação, nada recarrega sozinho no meio.
3. **Terminal 2, frontend** (pasta `frontend`): `npm run app:https` se for
   mostrar no celular com HTTPS (README 18.8), ou `npm run dev` para mostrar
   só no computador.
4. Abrir no navegador e deixar duas abas prontas:
   - aba 1: tela **Entrar** (`http://localhost:5173` ou o endereço HTTPS);
   - aba 2: `http://127.0.0.1:8000/docs` (documentação da API, para a parte técnica).
5. Zoom do navegador em 125% ou mais (o projetor diminui tudo) e, no Chrome,
   modo de celular (F12 → ícone de celular), que mostra o layout como no PDF.

### 1.3 Contas de exemplo

| Conta | Perfil | Para quê |
|---|---|---|
| `paula@exemplo.com.br` | administradora | quase toda a demonstração (Civic e moto) |
| `rafael@exemplo.com.br` | padrão | mostrar que um usuário não vê os dados de outro |

Senha das duas: `meu veiculo de exemplo` (não é segredo; está no código da carga).

---

## 2. Roteiro (cerca de 15 minutos)

### Bloco 1 — O problema e a proposta (1 min, sem tela)

> "Quem tem carro anota gastos, abastecimentos e revisões em lugares
> diferentes, ou não anota. O Meu Veículo junta tudo num lugar: cada pessoa
> acompanha os próprios veículos, quanto gasta, quanto o carro consome, o que
> precisa de manutenção e os problemas que apareceram. Funciona no computador
> e no celular, e pode ser instalado como aplicativo."

### Bloco 2 — Entrar e a tela Início (2 min)

1. Entre com `paula@exemplo.com.br`.
2. Na tela **Início**, mostre de cima para baixo:
   - os **gastos do mês**, em até três grupos (Manutenção, Combustível,
     Outros). Só aparecem os grupos que tiveram gasto: no começo do mês (no
     ensaio de 03/10, só "Outros", R$ 63,00), fale do grupo que estiver lá;
   - **Precisa de atenção**: revisão próxima, rodízio de pneus perto do km,
     problema aberto e conta vencida;
   - **Próximos gastos** (IPVA do ano que vem e renovação do seguro);
   - **Nível do tanque** com o marcador e o "≈" de estimativa;
   - consumo médio e custo por km.
3. Fala sugerida: *"Tudo o que aparece aqui é calculado pelo backend a partir
   dos registros. Quando falta informação, o sistema não inventa zero: mostra
   'dados insuficientes' e o motivo."*

### Bloco 3 — Abastecimento e consumo (3 min)

1. Toque em **Finanças** → aba **Combustível**.
2. Mostre o **consumo por mês**, as **marcações do tanque** e a lista de
   **abastecimentos** (gasolina e etanol).
3. Mostre o cartão **Etanol ou gasolina?**: toque em **Simular com os preços
   de hoje**, digite os dois preços e veja a recomendação. Fala: *"O limite
   vem do consumo real deste carro: 8,5 km/L com etanol dividido por 12,1 com
   gasolina dá 70%. Num carro que rende diferente, o limite muda."* (Com os
   dados de exemplo o limite coincide com os 70% da regra popular; vale dizer
   isso antes que alguém da banca pergunte.)
   Na lista **Marcações do tanque**, a marcação de 01/10 mostra um consumo
   estimado baixo (≈ 4,6 km/L) porque o trecho é de um dia só e a margem do
   marcador pesa muito: não precisa parar nela.
4. Registre um abastecimento ao vivo pelo atalho **Abastecer** do Início:
   informe dois dos três valores (litros, preço, total) e mostre que o
   sistema calcula o terceiro e confere o limite do tanque.

### Bloco 4 — Manutenção (2 min)

1. Toque em **Manutenção** → aba **Pendentes**: **Próximas** (revisão dos
   90 mil km agendada, em 18 dias; rodízio de pneus a 780 km) e **Em dia**
   (correia dentada, troca de óleo). Cada obrigação aparece uma vez só. Fala:
   *"Se uma passar do prazo, ela sobe para Atrasadas; sem dados para calcular,
   aparece em Dados insuficientes."* (Os dados de exemplo não têm nenhuma
   atrasada.)
2. Aba **Planos**: troca de óleo, rodízio de pneus e correia dentada, por km,
   por meses ou pelos dois.
3. Aba **Realizadas**: abra a troca de óleo e mostre peças e mão de obra
   separadas, com o total calculado pelo sistema.

### Bloco 5 — Diagnóstico (1 min)

1. Toque em **Diagnóstico**: o problema em aberto (barulho na suspensão
   dianteira), o resolvido por uma manutenção (rangido ao frear → pastilhas de
   freio) e o descartado (luz da injeção: tampa do tanque mal fechada).
2. Abra o barulho na suspensão e mostre a anotação e a foto; depois abra o
   rangido e mostre o vínculo com a manutenção que resolveu.

### Bloco 6 — Finanças (2 min)

1. **Finanças** → aba **Gastos**: alterne **Mês**, **Ano** e **Total**.
2. Mostre **Por categoria**, **Vencidas** e **Gastos futuros**.
3. Marque a conta vencida como paga e mostre que ela entra no mês do
   pagamento. Fala: *"Dinheiro é calculado com Decimal, nunca com número de
   ponto flutuante, e o total sempre vem do servidor."*

### Bloco 7 — Projetos e fotos *(opcional, 2 min)*

1. **Mais** → **Projetos**: "Som novo" concluído (R$ 1.450,00 de um
   orçamento de R$ 1.500,00), "Película nos vidros" em andamento e **acima do
   orçamento** (R$ 450,00 de R$ 400,00) e "Rodas aro 17" planejado.
2. Abra o "Som novo" e mostre as fotos de **antes e depois** (painel com o
   rádio original → central multimídia instalada) e os gastos dele.
3. **Mais** → **Meu veículo**: "Quanto esse carro já me custou" (no ensaio,
   R$ 77.030,01) por grupo (aquisição, combustível, manutenções, projetos,
   seguro, documentação, outros) e o custo por quilômetro.

### Bloco 8 — Histórico e administração *(opcional, 1 min)*

1. **Mais** → **Histórico**: tudo o que aconteceu com o carro, em ordem.
2. **Mais** → **Administração**: usuários e veículos, busca e perfil. Fala:
   *"O primeiro administrador só pode ser criado pelo terminal, e o banco
   impede desativar o último administrador."*

### Bloco 9 — Segurança: um usuário não vê o outro (1 min)

1. **Mais** → **Sair** (no fim da tela).
2. Entre com `rafael@exemplo.com.br`: ele só vê o Fiat Argo dele.
3. Fala: *"A permissão é conferida no servidor em toda leitura e gravação.
   Mesmo trocando o número do veículo no endereço, a resposta é 'não
   encontrado'."* Para provar: logado como Rafael, digite no endereço
   `/veiculos/2` (o Civic da Paula nos dados de exemplo) e mostre
   "Veículo não encontrado."

### Bloco 10 — Celular *(opcional, 1 min)*

Mostre o app instalado no Android (ícone, tela cheia). Se a rede do local
não deixar o celular falar com o computador, pule este bloco e diga que o
mesmo endereço funciona no celular pela rede de casa (README 18).

### Bloco 11 — Como foi construído (1 min)

Mostre a aba `http://127.0.0.1:8000/docs` (API documentada automaticamente) e
fale da arquitetura em camadas e dos testes. Os números estão no
`docs/apresentacao/resumo-para-o-tcc.md`, seção 7.

---

## 3. Plano B

| Se acontecer | Faça |
|---|---|
| A tela mostra "Não foi possível falar com o servidor" | o Terminal 1 parou: rode de novo o comando do backend (seção 1.2, item 2) |
| Aparecem os seus dados reais | o backend foi iniciado sem `$env:DB_NOME = "meu_veiculo_demo"`; pare (`Ctrl + C`) e inicie de novo no mesmo terminal com a linha do `$env:` |
| O celular não conecta na rede do local | mostre no computador com o modo de celular do Chrome (F12) |
| Algum dado ficou estranho depois de um ensaio | `gerenciar.py carregar-exemplo --recomecar` (pare o backend antes) |
| O projetor corta a tela | diminua o zoom do navegador (`Ctrl` + `-`) |
| Internet do local caiu | não faz diferença: o sistema roda inteiro no computador |

Levar também: carregador, cabo USB do celular e, se possível, um vídeo curto
da demonstração gravado no ensaio (caso o computador falhe).

---

## 4. Perguntas prováveis da banca

As principais estão abaixo. A lista completa, por assunto (57 perguntas
com respostas sugeridas), está em
`docs/apresentacao/perguntas-da-banca.md`.

**Por que aplicativo web instalável (PWA) e não um app nativo?**
Um só código para computador e celular, sem loja de aplicativos e sem
aprender outra linguagem. Instalado, ele abre com ícone e tela cheia. A
comparação completa está em `docs/decisoes.md` (29/09).

**Como os dados ficam protegidos?**
Só o backend acessa o PostgreSQL. Senhas com Argon2id (só o hash é guardado).
Sessão em cookie `HttpOnly` (o JavaScript não lê). Toda gravação exige um
cabeçalho que só o app envia. A permissão é conferida no servidor em toda
rota: dono do veículo ou administrador, senão "não encontrado".

**Como o consumo é calculado?**
Entre dois pontos em que se sabe quanto falta para encher o tanque (tanque
cheio, nível do marcador ou marcação), dividindo os km rodados pelos litros
abastecidos no trecho. Sem dois pontos assim, o sistema mostra "dados
insuficientes" em vez de um número errado.

**Por que PostgreSQL e não SQLite?**
O banco original usa domains, views e triggers do PostgreSQL. Os testes rodam
num PostgreSQL de teste real para provar que essas regras funcionam.

**Como o banco evoluiu sem perder dados?**
O SQL recebido nunca foi editado. Cada mudança é uma migration numerada
(0002 a 0014) e, antes de criar uma restrição nova, a migration procura dados
antigos incompatíveis e para mostrando quais são, sem apagar nada.

**Na recuperação de senha, o sistema diz se o e-mail existe. Isso não é um risco?**
É, e foi uma escolha consciente. O pedido original dizia para não revelar e
limitar tentativas. Depois de usar o sistema, decidi priorizar quem digitou o
e-mail errado. A troca e os riscos aceitos estão registrados em
`docs/decisoes.md` (02/10). O login continua com limite de tentativas.

**O que ficou de fora?**
Funcionar sem internet (offline), iPhone, hospedagem fora de casa e backup
automático. Veja a seção 8 do resumo.
