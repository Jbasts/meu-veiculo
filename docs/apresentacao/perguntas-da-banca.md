# Possíveis perguntas da banca — Meu Veículo

Perguntas que a banca do TCC pode fazer, com respostas sugeridas e o lugar
do projeto onde está a prova. As respostas são um ponto de partida: fale com
as suas palavras e, sempre que puder, **mostre no sistema ou no código** em vez
de só explicar. Números conferidos em 03/10/2026.

Onde encontrar mais detalhes:
- `docs/decisoes.md`: cada decisão técnica, com data, motivo e alternativas;
- `docs/apresentacao/resumo-para-o-tcc.md`: arquitetura, banco, segurança e números;
- `README.md`: instalação, uso e o que foi testado (seção 19).

**Dica geral:** quando não souber, diga "não sei, mas sei onde procurar" e
mostre o `decisoes.md` ou o teste correspondente. Banca valoriza quem conhece
os limites do próprio trabalho.

---

## 1. Problema e escopo

**1.1 Qual problema o sistema resolve?**
Quem tem carro anota gastos, abastecimentos e revisões em lugares diferentes,
ou não anota. O Meu Veículo junta tudo e calcula o que a pessoa normalmente
não sabe: quanto o carro consome de verdade, quanto custa por quilômetro,
quanto já custou no total e o que precisa de manutenção.

**1.2 Quem é o usuário?**
Qualquer pessoa com um ou mais veículos (carro, moto, flex, elétrico...). Há
dois perfis: **padrão** (vê só o que é seu) e **administrador** (vê todos os
usuários e veículos).

**1.3 O que o sistema faz, em resumo?**
Cadastro de veículos e quilometragem; abastecimentos e consumo; manutenções e
planos recorrentes; diagnósticos (problemas do carro); gastos e finanças;
projetos de melhoria com orçamento; fotos (inclusive de antes e depois);
histórico; tela inicial com alertas; administração de usuários.

**1.4 Existe algo parecido no mercado? O que o seu tem de diferente?**
Existem aplicativos de controle de abastecimento. Os diferenciais aqui:
- consumo calculado também com o **nível do marcador**, não só com tanque cheio;
- "Etanol ou gasolina?" com o consumo real do carro, não com a regra fixa de 70%;
- diagnósticos ligados à manutenção que os resolveu;
- projetos com orçamento e fotos de antes e depois;
- dados na própria máquina da pessoa, sem depender de empresa.

*(Se a banca pedir nomes de concorrentes, cite os que você pesquisou no texto
do TCC; não invente comparação na hora.)*

**1.5 O que ficou fora do escopo?**
Funcionar sem internet (offline), iPhone/Safari, hospedagem para uso fora de
casa, backup automático agendado, relatórios em PDF/planilha, lembretes por
e-mail. Está na seção 8 do resumo.

---

## 2. Plataforma e tecnologias

**2.1 Por que aplicação web instalável (PWA) e não aplicativo nativo?**
Um só código para computador e celular, sem loja de aplicativos, sem conta
paga e sem precisar de Mac. Instalado, abre com ícone e tela cheia. A câmera
funciona pelo campo de foto do navegador. React Native e Flutter foram
avaliados e descartados: exigiriam outro código ou outra linguagem sem ganho
para as funções do sistema (`decisoes.md`, 29/09).

**2.2 Por que React, FastAPI e PostgreSQL?**
- React: muito usado, com componentes reutilizáveis; TypeScript pega erros antes de rodar.
- FastAPI: Python, validação automática dos dados (Pydantic) e documentação da
  API gerada sozinha (mostre `http://127.0.0.1:8000/docs`).
- PostgreSQL: o banco original já usava recursos dele (domains, views,
  triggers); é robusto e gratuito.
Também era a sua preferência declarada no início do projeto.

**2.3 Por que não SQLite, que é mais simples?**
Porque não comprova os recursos do PostgreSQL que o sistema usa. Os testes
rodam num PostgreSQL de teste real, separado do banco de desenvolvimento.

**2.4 O sistema funciona sem internet?**
Não. Ele não precisa de internet, mas precisa falar com o computador onde o
backend roda (pela rede de casa). Sem conexão, o app instalado mostra a página
"Sem conexão com o servidor". Offline completo exigiria guardar e sincronizar
dados no celular, o que foi deixado de fora de propósito.

**2.5 Como o celular acessa o sistema?**
Pelo Wi-Fi de casa: o celular abre o endereço do computador
(`http://IP:5173` ou, com HTTPS, `https://IP:4173`). O celular só fala com o
frontend; o frontend repassa `/api` ao backend, que escuta só no próprio
computador. O PostgreSQL nunca fica exposto na rede (README, seção 18).

**2.6 Para que serve o HTTPS se é só na rede de casa?**
O navegador só permite instalar o app e usar o service worker em contexto
seguro. Com o mkcert, cria-se um certificado próprio, instalado no computador
e no celular, sem custo e sem sair da rede (README 18.8).

---

## 3. Arquitetura e código

**3.1 Explique a arquitetura do backend.**
Em camadas: **Route → Controller → Service → Repository → banco**. Route
declara o endereço; controller traduz HTTP; service tem as regras e as
transações; repository tem todo o SQL. Mostre um exemplo real: `GET /api/saude`
(README, seção 3.3).

**3.2 Por que separar em tantas camadas?**
Cada parte tem um motivo para mudar: trocar uma regra não mexe no SQL, mudar
uma tela não mexe na regra. As regras podem ser testadas sem servidor web.

**3.3 Como garantir que ninguém "fure" as camadas?**
Um teste automático (`tests/test_arquitetura.py`) lê os imports de cada
arquivo e falha se, por exemplo, um service importar FastAPI. Outro
(`tests/test_entities.py`) compara as classes com o banco real.

**3.4 Como você acrescentaria uma funcionalidade nova?**
Seguindo o roteiro do README (seção 3.5): migration (se mudar o banco),
entity, repository, service, schema, controller, route, dependência, testes e
tela. Exemplo recente: a confirmação de e-mail (migration 0014).

**3.5 O frontend segue a mesma arquitetura?**
Não: segue a organização comum de React (pages, components, services, types,
hooks). Um único módulo (`services/apiCliente.ts`) faz todas as chamadas à
API e trata erros, sessão perdida e falta de conexão.

**3.6 Quantas linhas, telas e endpoints?**
95 endpoints, 35 telas, cerca de 11.600 linhas no backend e 12.300 no
frontend (sem testes), cerca de 13.000 linhas de testes.

---

## 4. Banco de dados

**4.1 O que você mudou no banco original?**
Nada no arquivo original: ele é somente leitura e conferido por SHA-256. Tudo
entrou como migrations numeradas (0002 a 0014): autenticação, leituras de
quilometragem, manutenções e itens, diagnósticos, gastos, abastecimentos,
projetos, tanque, fotos no banco e confirmação de e-mail. Hoje são 18
tabelas, 5 views e 14 triggers.

**4.2 Quais problemas você encontrou no SQL original?**
Exemplos (lista completa na etapa 0 e em `decisoes.md`): registros vinculados
podiam ser de veículos diferentes (foto de um carro ligada à manutenção de
outro); não havia histórico das leituras de quilometragem; não havia estrutura
de recuperação de senha; abastecimento usava litros mesmo para GNV.

**4.3 O que acontece se a migration encontrar dados antigos errados?**
Ela para e lista os registros com problema, sem apagar, unir ou inventar
valores. A pessoa corrige e roda de novo. Antes de migrar um banco que já tem
dados, o comando faz backup com `pg_dump`.

**4.4 Por que as regras também estão no banco, e não só na API?**
Para valerem mesmo com acesso direto (pgAdmin). Exemplos: o banco não deixa o
sistema ficar sem administrador ativo, recusa vínculos entre veículos
diferentes e recalcula a quilometragem atual a partir das leituras.

**4.5 Por que as fotos ficam dentro do banco?**
Decisão sua (migration 0013): tudo num lugar só, e o backup do banco leva as
fotos junto. A imagem fica numa tabela separada (`foto_conteudo`) para as
listagens não carregarem os bytes. Contra: o banco cresce; com o volume de
um uso pessoal, não é problema.

**4.6 Como o sistema funciona com o banco vazio?**
Funciona: as migrations criam só a estrutura. Os dados de exemplo ficam num
banco separado (`meu_veiculo_demo`), com uma trava que impede gravar nos dados
reais.

---

## 5. Regras de negócio e cálculos

**5.1 Como o consumo é calculado?**
Entre dois pontos em que se sabe quanto falta para encher o tanque: tanque
cheio (exato), nível do marcador antes de abastecer ou marcação do tanque
(com margem). Consumo = km rodados no trecho ÷ litros abastecidos no trecho.
Sem dois pontos assim, aparece "dados insuficientes".

**5.2 Por que o consumo às vezes aparece com "≈" e uma faixa?**
Porque o marcador tem margem (a agulha não é exata). O sistema mostra a faixa
possível ("entre 8,4 e 8,6"). Quanto mais quilômetros no trecho, menor a margem.

**5.3 Como funciona o "Etanol ou gasolina?"**
O limite é a razão entre os consumos reais do carro com etanol e com
gasolina. Nos dados de exemplo dá 70% (8,5 ÷ 12,1), igual à regra popular,
mas num carro que rende diferente o limite muda.

**5.4 Como vocês tratam dinheiro?**
Sempre com `Decimal`, nunca com número de ponto flutuante, arredondando meio
para cima em centavos. O total é calculado no servidor; o valor que vem da
tela não é confiado. *(Se perguntarem por quê: `0,1 + 0,2` em ponto flutuante
dá `0,30000000000000004`.)*

**5.5 E as datas?**
Campos de data são guardados sem hora, sem conversão de fuso. As regras de
calendário (hoje, mês, vencimento) usam `America/Sao_Paulo`, para um gasto de
31/10 à noite não cair em novembro.

**5.6 Por que o sistema mostra "dados insuficientes" em vez de zero?**
Porque zero é uma informação falsa: consumo zero ou custo zero levaria a uma
conclusão errada. O sistema diz que não sabe e explica o motivo.

**5.7 Como funciona o custo por km?**
Despesas do período ÷ km rodados no mesmo período, começando na compra (data
e km) quando essas informações existem e são coerentes com as leituras. O
valor de compra entra no custo total, mas não no custo por km.

**5.8 Como a manutenção sabe o que está próximo ou atrasado?**
Pelos planos (a cada X km, Y meses ou os dois), comparando com a última
manutenção do tipo e a quilometragem/data atuais. Cada obrigação aparece uma
vez só, mesmo que exista também uma manutenção agendada para ela.

**5.9 Por que "Atualizar km" pede o nível do combustível?**
Pedido seu, para melhorar o cálculo do consumo: cada atualização vira uma
marcação do tanque, que serve de ponto para o cálculo e para estimar o nível
atual na tela inicial.

---

## 6. Segurança

**6.1 Como as senhas são guardadas?**
Só o hash, com Argon2id (algoritmo recomendado pela OWASP e pela RFC 9106),
com sal aleatório por senha. A senha nunca é gravada nem devolvida.

**6.2 Por que não exigir maiúscula, número e símbolo?**
Porque isso leva a senhas previsíveis como "Senha@123". A política aceita de
8 a 128 caracteres, incentiva frases e recusa as senhas mais comuns e a senha
igual ao e-mail (recomendação atual do NIST).

**6.3 Como funciona o login?**
Sessão guardada no servidor (só o hash do token no banco) e um cookie
`HttpOnly` (o JavaScript não lê), `SameSite=Lax` e restrito a `/api`. Dura 30
dias. Sair encerra a sessão no banco. O login tem limite: 5 erros por e-mail
ou 20 por endereço de rede em 15 minutos.

**6.4 Como impedir que um usuário veja os dados de outro?**
A permissão é conferida no servidor em **toda** leitura e gravação, inclusive
listagens e fotos: só o dono do veículo ou um administrador. Senão, a
resposta é "não encontrado", que não revela se o registro existe. Mostre ao
vivo: logado como Rafael, abrir `/veiculos/2`.

**6.5 O que é CSRF e como foi tratado?**
É outro site fazer o navegador da pessoa enviar um pedido usando a sessão
dela. Toda gravação exige o cabeçalho `X-MV-Requisicao: 1`, que só o próprio
app consegue enviar; junto com o `SameSite=Lax` do cookie, bloqueia esse ataque.

**6.6 Como funciona a recuperação de senha?**
Link de uso único, válido por 60 minutos, com só o hash do token guardado. A
troca da senha e o uso do link acontecem na mesma transação: se dois pedidos
chegarem juntos com o mesmo link, só um funciona (há teste disso). Depois da
troca, todas as sessões da conta são encerradas.

**6.7 A recuperação diz se o e-mail existe. Isso não é um risco?**
É, e foi uma escolha consciente. O pedido original dizia para não revelar e
para limitar tentativas nessa tela. Depois de usar o sistema, você decidiu
priorizar quem digita o e-mail errado: aparece "E-mail não existente, digite
novamente" e não há limite nessa tela. Os riscos aceitos (descobrir quais
e-mails têm conta; muitos pedidos para o mesmo e-mail) estão em
`decisoes.md` (02/10). O login manteve o limite. *(Se perguntarem como
voltaria atrás: a resposta sempre igual e o limite já existiram e estão no
histórico do Git.)*

**6.8 Para que serve a confirmação de e-mail?**
Garante que o e-mail da conta é da pessoa antes de ela usar o sistema, porque
é para ele que vão os links de senha. O link vale 48 horas e é de uso único;
contas anteriores à regra continuam entrando.

**6.9 E as fotos? Uma foto pode ter vírus ou a localização da pessoa?**
O tipo é conferido pelo conteúdo (não pelo nome do arquivo): JPEG, PNG, WebP e
HEIC (convertido para JPEG). A imagem é regravada do zero, o que remove
conteúdo escondido e os metadados, inclusive a localização GPS. Tamanho
limitado a 10 MB e lado maior reduzido a 2560 pontos. A foto só é entregue a
quem tem acesso ao veículo.

**6.10 Onde ficam as senhas do sistema (banco, e-mail)?**
Só no `backend\.env`, que não vai para o Git. Nada de segredo no frontend
nem em logs: uma falha de e-mail aparece no log só com o tipo do erro.

**6.11 Como o primeiro administrador é criado?**
Pelo terminal (`gerenciar.py promover-admin EMAIL`), que exige a senha do
banco. Não existe senha fixa nem endereço da API para virar admin.

---

## 7. Testes e qualidade

**7.1 Como você sabe que o sistema funciona?**
Testes automáticos executados: **796 no backend** (API e banco reais) e
**224 no frontend**, todos passando, além da verificação de tipos do
TypeScript. E cada etapa foi validada por você com os seus dados, no
computador e no celular (`progresso.md`).

**7.2 O que os testes cobrem? Dê exemplos.**
- cada migration aplicada num banco com dados antigos incompatíveis;
- um usuário tentando acessar o veículo de outro, em todas as rotas;
- dois pedidos simultâneos usando o mesmo link de recuperação;
- totais financeiros sem contar duas vezes;
- consumo, nível do tanque e "dados insuficientes";
- envio de e-mail com um servidor SMTP de teste;
- a arquitetura em camadas.

**7.3 Por que testar no PostgreSQL real e não com dados falsos (mocks)?**
Porque parte das regras está no banco (triggers, views, restrições). Testar
com outro banco ou com simulação não provaria que elas funcionam.

**7.4 Existe algum problema conhecido?**
Sim, e ele está registrado: um teste de concorrência (dois administradores
rebaixando um ao outro no mesmo instante) falha raramente. Nesse caso extremo,
um dos pedidos pode terminar em erro interno em vez da mensagem do último
administrador. O banco nunca fica sem administrador; o problema é só a
mensagem. Está anotado em `progresso.md` para investigar. *(Dizer isso
mostra domínio do projeto.)*

**7.5 Como você faria o deploy (publicação)?**
Hoje roda no computador de casa. Para publicar: hospedar backend e banco num
servidor com HTTPS e domínio, servir o frontend gerado pelo `npm run build`,
`COOKIE_SEGURO=true`, backup agendado do banco. Ficou fora do escopo.

---

## 8. Processo de desenvolvimento e uso de IA

**8.1 Como foi organizado o desenvolvimento?**
Em etapas (0 a 12), cada uma com código, testes executados, validação sua e
commit antes da seguinte. Decisões registradas em `decisoes.md`, andamento em
`progresso.md`, guia completo no `README.md`.

**8.2 Você usou inteligência artificial?**
Responda com transparência, porque está registrado no próprio projeto
(`decisoes.md`, primeira linha: desenvolvimento com o Claude Code). Pontos que
mostram o seu papel:
- você definiu o problema, o escopo, as prioridades e as regras (por exemplo,
  nível do combustível ao atualizar o km, gastos futuros, fotos no banco,
  confirmação de e-mail, mudança na recuperação de senha);
- você testou e validou cada etapa com os seus dados e no seu celular;
- você decidiu entre alternativas e ficou com a responsabilidade pelas
  escolhas, inclusive as que contrariaram o pedido original;
- cada decisão tem motivo registrado, e todos os testes foram executados.

*Antes da banca, confira as regras da sua instituição e do seu orientador
sobre uso de IA e cite a ferramenta no texto do TCC, na metodologia.*

**8.3 Então você entende o código?**
Prepare-se para explicar, com o código aberto, pelo menos um fluxo completo.
Sugestão: **registrar um abastecimento**, da tela
(`frontend/src/pages/AbastecimentoFormPage.tsx`) até a rota, o service
(`backend/app/services/abastecimento_service.py`), o repository e a tabela.
Ou o login, da `LoginPage.tsx` ao `autenticacao_service.py`.

**8.4 Qual foi a maior dificuldade?**
Resposta pessoal. Candidatos com história para contar, todos registrados:
- o cálculo de consumo com o nível do marcador (decisões de 01/10);
- evoluir o banco original sem perder dados (migrations com conferência prévia);
- as permissões em todas as rotas;
- acessar pelo celular (rede, firewall, HTTPS).

**8.5 O que você faria diferente?**
Resposta pessoal. Ideias honestas: definir desde o início regras que mudaram
depois (recuperação de senha, confirmação de e-mail), ou planejar a
hospedagem para uso fora de casa.

**8.6 Você vai continuar usando o sistema?**
Sim, é a intenção desde o início: o README foi escrito para você conseguir
rodar, entender e continuar sozinha.

---

## 9. Trabalhos futuros

**9.1 O que você acrescentaria numa próxima versão?**
Lembretes por e-mail de manutenção e vencimentos; relatórios em PDF/planilha;
gráficos de gastos e consumo; backup automático agendado; hospedagem com
HTTPS para uso fora de casa; funcionamento offline com sincronização; validar
no iPhone; leitura da nota fiscal (cupom) pela câmera.

**9.2 O sistema aguenta muitos usuários?**
Foi feito para uso pessoal ou familiar. As listagens que crescem são
paginadas e as consultas usam índices, mas não houve teste de carga. Para
muitos usuários, seria preciso hospedagem própria, monitoramento e esse teste.
