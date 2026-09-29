> **Nota do kit:** este é o pedido original da Paula, sem alterações. Neste repositório, os anexos citados abaixo como "Meu Veículo — Telas Mobile(10).pdf" e "meu_veiculo_banco(6).sql" estão em `docs/telas-mobile.pdf` e `database/original/meu_veiculo_banco.sql`. Onde o texto diz "nesta conversa", leia "neste repositório".

---

Quero desenvolver do zero um aplicativo chamado Meu Veículo, usando as telas e o banco de dados que estou anexando. Quero o projeto completo: interface, backend, integração com PostgreSQL, testes e instruções para executar no Windows com VS Code e testar no celular.

O objetivo é permitir que cada usuário acompanhe seus veículos, gastos, abastecimentos, manutenções, problemas, projetos de melhoria e fotos. Tenho preferência por explicações passo a passo, com exemplos concretos. Quero conseguir executar, entender e continuar o projeto.

REFERÊNCIAS E PRIMEIRA RESPOSTA

Os anexos desta conversa são:
- Meu Veículo — Telas Mobile(10).pdf: referência visual das telas e dos fluxos.
- meu_veiculo_banco(6).sql: estrutura inicial do PostgreSQL, incluindo tabelas, relacionamentos, restrições, funções, triggers e views.

Os números entre parênteses fazem parte dos nomes das cópias anexadas. Trabalhe com os arquivos efetivamente disponíveis nesta conversa. Não presuma o conteúdo de versões anteriores. Se não conseguir ler um anexo, identifique o problema antes de implementar a parte que depende dele.

Analise integralmente os dois arquivos antes de começar. Use o PDF como referência de aparência e navegação e o SQL como base da implementação. Os nomes, veículos, datas, valores, percentuais e indicadores das telas são exemplos; todos os dados reais devem vir do banco.

Minha primeira decisão será sobre a plataforma. Na primeira resposta:
1. Resuma sua compreensão do sistema e demonstre que leu os anexos, citando telas, tabelas e regras concretas.
2. Aponte inconsistências e ajustes necessários no banco, separando o que já existe do que precisa ser acrescentado ou corrigido.
3. Compare uma aplicação web responsiva/PWA com um aplicativo mobile nativo ou multiplataforma. Diferencie instalação pelo navegador de distribuição como aplicativo mobile e explique execução no computador, uso no Android/iPhone, câmera, atualização e publicação.
4. Recomende uma stack simples e organizada para cada alternativa relevante, mantendo PostgreSQL. Explique o papel do frontend, da API e do banco em linguagem acessível.
5. Pergunte apenas o indispensável: plataforma desejada e celulares que pretendo usar. Outras decisões técnicas rotineiras podem ser propostas com justificativa.
6. Apresente as etapas de implementação e aguarde minha resposta sobre a plataforma antes de definir ou gerar o frontend.

Não gere o projeto inteiro nessa primeira resposta. Após alinharmos a plataforma, avance com a implementação por etapas executáveis até concluir o escopo abaixo.

As regras funcionais deste pedido prevalecem sobre números ilustrativos do PDF e sobre comportamentos incorretos do SQL. Preserve a estrutura existente sempre que possível e explique qualquer alteração necessária. Não copie um erro apenas porque ele aparece em um anexo.

ESCOPO FUNCIONAL

1. Cadastro, login e conta

- Cadastro com nome, e-mail, senha e confirmação de senha; login, logout, alteração de senha e recuperação de acesso.
- Validação no frontend e no backend, com mensagens em português. E-mail único sem diferenciar maiúsculas de minúsculas, com remoção de espaços nas extremidades e tratamento de conflito de unicidade.
- Senhas com hash seguro, nunca armazenadas ou retornadas em texto puro. Explique o algoritmo e a política de senha adotados.
- Novos usuários começam com perfil padrao. O cadastro público não aceita a escolha de admin, mesmo com uma requisição manipulada.
- Contas desativadas não acessam o sistema, inclusive com uma sessão ou token emitido antes da desativação.
- Recuperação com links temporários de uso único. Guarde apenas o hash do token de recuperação, com validade e controle de uso. A troca de senha e o consumo do token precisam ocorrer de forma atômica, inclusive em tentativas simultâneas.
- Documente como configurar o envio de e-mail e uma alternativa local de desenvolvimento para testar a mensagem sem depender de um serviço pago. Não declare entrega de e-mail real como testada sem evidência.
- Evite revelar se um e-mail está cadastrado pela resposta da recuperação. Proteja login e recuperação contra tentativas excessivas.
- Defina expiração, logout e invalidação de sessões após recuperação de senha. Nenhuma senha ou segredo deve ser exposto ao frontend ou aos logs.

2. Perfis e permissões

- O usuário padrão acessa apenas os próprios veículos e registros. O administrador visualiza e gerencia usuários, veículos e registros de todos.
- Verifique permissões no backend em leitura e escrita, incluindo listagens, buscas, indicadores, anotações, itens de projeto e acesso ao conteúdo das fotos.
- Não confie no usuario_id, veiculo_id, perfil ou IDs relacionados enviados pelo frontend. Confira a propriedade e a relação entre os registros envolvidos.
- Rejeite vínculos entre registros de veículos diferentes, mesmo que os veículos pertençam ao mesmo usuário. Administradores também devem respeitar essa consistência.
- Explique como criar o primeiro administrador com segurança, sem credenciais fixas e sem um endpoint público de promoção.
- Impeça a desativação ou o rebaixamento do último administrador ativo.

3. Veículos

- Cadastro, edição, listagem e seleção do veículo em uso, permitindo vários veículos por usuário.
- Campos conforme o SQL e as telas: marca, modelo, versão, ano, placa, cor, combustível, quilometragem e dados da aquisição.
- Foto de capa e galeria; atualização manual da quilometragem; inativação preservando todo o histórico.
- Preserve a regra UNIQUE (usuario_id, placa): a unicidade é por proprietário. Normalize a placa de forma consistente, por exemplo, letras maiúsculas e remoção de hífen e espaços, sem transformar silenciosamente a regra em unicidade global.
- Antes de normalizar dados existentes, detecte colisões e apresente os registros em conflito. Não apague nem una veículos automaticamente.
- Registros históricos não podem reduzir automaticamente a quilometragem atual. Manutenções apenas agendadas não podem aumentá-la.
- Registre a data da leitura da quilometragem e diferencie-a da data em que o registro foi inserido, quando necessário. A tela deve mostrar uma data de atualização confiável.
- Defina um procedimento explícito para corrigir uma quilometragem digitada incorretamente, com preservação do histórico e recálculo dos indicadores afetados.

4. Tela inicial

- Veículo selecionado e quilometragem atual; atalhos para abastecimento, gasto, manutenção e registro de problema.
- Alertas de manutenção atrasada ou próxima e diagnósticos pendentes.
- Resumo dos gastos do mês por categoria, consumo médio e custo por quilômetro.
- Todos os indicadores calculados com registros reais e com o período de referência informado.
- Estados adequados para usuário sem veículo, veículo sem registros e dados insuficientes para calcular um indicador. Não use zero para representar um indicador desconhecido.

5. Manutenções e planos

- Abas de pendentes, realizadas e planos; cadastro e edição de planos recorrentes por quilometragem, meses ou ambos.
- Manutenções avulsas ou vinculadas a um plano, realizadas ou agendadas, com descrição, sistema, data, quilometragem, valor, oficina, garantia e observações.
- Situação calculada como em dia, próxima ou atrasada, considerando o limite de tempo ou quilometragem atingido primeiro. Use inicialmente até 1.000 km ou 30 dias para a faixa de manutenção próxima e documente os limites exatos das classificações.
- Mantenha uma data-base e uma quilometragem-base consistentes quando não existir manutenção anterior. Não use uma data que muda a cada consulta nem invente uma leitura de zero quando a base for desconhecida.
- Trate planos recorrentes e manutenções avulsas/agendadas na aba de pendentes, evitando alertas duplicados para a mesma obrigação.
- Ao editar, concluir ou reclassificar uma manutenção, atualize os indicadores relacionados. Mudar de agendada para realizada deve considerar sua quilometragem mesmo quando apenas o status for alterado.
- Explique se garantia_km representa um limite absoluto do hodômetro ou uma distância de cobertura. Mantenha o significado consistente no formulário, banco e alertas.
- Se houver limites de garantia por data e km, considere o que vencer primeiro. Falta de informação não significa garantia confirmada.

6. Diagnósticos

- Cadastro de problemas com título, descrição, sistema, gravidade, data e quilometragem.
- Filtros de abertos, resolvidos e todos; estados aberto, em observação, resolvido e descartado.
- Detalhamento com anotações e fotos; aviso de possível garantia em uma manutenção realizada do mesmo veículo e sistema, sem garantir que o novo problema tenha cobertura.
- Fluxo Resolver com uma manutenção: preencher os dados relacionados e, após salvar uma manutenção realizada, vincular os registros e marcar o diagnóstico como resolvido, com data de resolução.
- Execute a criação da manutenção e a resolução do diagnóstico na mesma transação. Se qualquer parte falhar, nenhuma delas pode ficar concluída isoladamente.
- Salvar uma manutenção agendada não resolve o diagnóstico. Evite a criação duplicada por envio repetido da mesma ação.
- Defina o comportamento de edição, exclusão ou mudança de status de uma manutenção vinculada para não deixar a resolução incoerente.

7. Finanças e gastos

- Abas de gastos e combustível; seleção de mês e ano; totais, distribuição por categoria e listagem dos lançamentos.
- Cadastro e edição de gastos nas categorias do SQL; controle de pago, pendente e vencimento; exibição de contas a vencer e vencidas.
- Integre valores de manutenções realizadas, abastecimentos, gastos pagos e itens dos projetos sem duplicar despesas. Não crie automaticamente uma cópia em gasto para um valor que já entra no total pela tabela de origem.
- Exclua manutenções agendadas e gastos ainda pendentes do total de despesas efetivadas, mantendo sua visualização separada.
- Defina e documente qual data determina o mês de um gasto pago. Se a regra exigir data_pagamento, acrescente o campo por migration e trate datas antigas desconhecidas sem inventar informações.
- Editar um lançamento ou mudar seu estado de pagamento deve refletir nos totais. Cancelar um projeto não apaga despesas que realmente ocorreram.
- Use aritmética decimal para dinheiro e defina arredondamento. O backend é a fonte dos totais e não deve confiar no cálculo recebido do frontend.

8. Abastecimentos e consumo

- Combustível, data, quilometragem, quantidade, preço unitário, valor total, posto e indicação de tanque cheio; histórico e edição dos registros.
- Calcule e valide o total no backend com uma regra explícita de arredondamento e tratamento de divergências em centavos.
- Calcule o consumo entre dois abastecimentos de tanque cheio: distância entre as leituras dividida pela quantidade abastecida depois do cheio inicial até o cheio final, incluindo os abastecimentos parciais intermediários e o cheio final, mas excluindo a quantidade do cheio inicial.
- Exemplo de teste, considerando o mesmo combustível e um ciclo válido: cheio inicial aos 10.000 km; parcial de 10 litros aos 10.100 km; cheio final de 20 litros aos 10.300 km. Resultado: 300 / (10 + 20) = 10 km/L.
- Para médias de vários ciclos válidos, use a distância total dividida pela quantidade total correspondente, evitando uma média aritmética simples dos valores em km/L.
- O primeiro tanque cheio sozinho não permite calcular consumo. Informe claramente quando faltarem dados ou quando um ciclo for inválido.
- Defina ordenação consistente para registros no mesmo dia e valide a cronologia das leituras sem impedir o lançamento de dados antigos válidos. Recalcule os ciclos afetados por edição ou inclusão histórica.
- Compare etanol e gasolina usando consumos específicos confiáveis e preços registrados. O limite de compensação é consumo do etanol / consumo da gasolina, comparado à razão entre seus preços; não fixe sempre em 70%.
- Informe as datas e a origem dos preços usados. Não apresente preços antigos como uma cotação atual.
- Trate mistura e troca de combustível: não atribua todo o consumo de um intervalo ao combustível abastecido no final. Identifique ciclos mistos ou de transição e explique as limitações e o efeito do combustível residual. Exclua ciclos sem base confiável da comparação por combustível, apresentando dados insuficientes quando necessário.
- O SQL permite tipos de veículo e combustíveis além dos botões ilustrados no PDF. Documente a compatibilidade de cada opção. GNV precisa de unidade coerente, como m³; não apresente seu consumo em km/L. Em veículos elétricos, indicadores de combustível líquido devem aparecer como não aplicáveis. Um módulo específico de recarga elétrica é uma extensão a discutir, não um recurso a inventar silenciosamente.

9. Projetos de melhoria

- Cadastro e edição com nome, descrição, categoria, orçamento, previsão e status: planejado, em andamento, concluído e cancelado.
- Inclusão, edição e exclusão de itens de gasto, com atualização dos totais e do histórico.
- Total gasto, percentual do orçamento e valor restante ou excedido. Trate orçamento ausente ou igual a zero sem divisão por zero.
- Fotos de antes e depois; conclusão com registro de data; comportamento consistente caso o projeto seja reaberto.

10. Fotos

- Captura pela câmera ou seleção da galeria, conforme a plataforma escolhida; legenda, data e definição da foto de capa.
- Vínculo opcional com um projeto, diagnóstico ou manutenção do mesmo veículo, respeitando a regra de no máximo um vínculo por foto. Fotos de antes/depois exigem vínculo com projeto.
- Filtros por tipo de vínculo e no máximo uma foto de capa por veículo. Trocar a capa deve ser uma operação consistente, inclusive em requisições concorrentes.
- Valide formato, conteúdo real do arquivo e tamanho de até 10.485.760 bytes, conforme o SQL. Não confie apenas na extensão ou no tipo MIME informado pelo cliente.
- Explique como tratar HEIC, permitido pelo SQL, inclusive a visualização na plataforma escolhida. Se houver conversão, mantenha metadados coerentes e documente a política.
- Armazene os arquivos separados dos metadados do PostgreSQL, com nomes gerados pelo backend e acesso protegido. Conhecer a URL de uma foto não pode permitir acesso sem autorização.
- Trate falhas entre gravação do arquivo e gravação no banco, limpeza de arquivos órfãos e exclusões relacionadas. O banco apagar metadados por cascata não remove automaticamente o arquivo do armazenamento.

11. Histórico e custo do veículo

- Histórico integrado, ordenado por data, com filtros por período e tipo e acesso ao detalhe de cada lançamento.
- Custo total do veículo incluindo aquisição e despesas registradas, sem duplicar valores.
- Custo por quilômetro sem incluir aquisição, conforme o PDF. Use despesas e distância percorrida do mesmo período e identifique esse período na tela.
- Para o indicador desde a compra, use a data e a quilometragem da aquisição quando disponíveis e confiáveis. Trate compra sem valor informado, bases incompletas e distância percorrida igual a zero.
- Sem base suficiente, informe que não é possível calcular ou apresente um período alternativo claramente identificado e sustentado por leituras reais. Não invente distâncias mensais a partir da quilometragem atual.
- Avalie a necessidade de uma tabela de leituras de quilometragem: armazenar apenas a última atualização não permite reconstruir qualquer período histórico com precisão.
- A view vw_historico atual reúne lançamentos financeiros efetivados. Preserve sua finalidade e explique como eventuais eventos sem valor, como diagnósticos, serão exibidos sem alterar indevidamente totais financeiros.

12. Administração

- Listagem e busca de usuários por nome ou e-mail; filtros por perfil.
- Visualização de veículos de cada usuário e do último acesso.
- Alteração de perfil, ativação/desativação da conta e ação para iniciar recuperação de senha, sem revelar ou definir uma senha fixa.
- Área e endpoints administrativos acessíveis somente a administradores. Ocultar o menu não substitui a proteção do backend.
- Inclua paginação nas listagens que podem crescer e ordenação estável para evitar itens repetidos ou omitidos entre páginas.

REVISÃO E EVOLUÇÃO DO POSTGRESQL

Revise o SQL antes da integração e forneça migrations ou scripts incrementais versionados. Preserve dados existentes. Separe instalação em banco vazio de atualização de um banco já criado; não oriente a executar o script inicial novamente em um banco existente.

Verifique especificamente estes pontos identificados no SQL anexado:
- trg_km_manutencao dispara em INSERT ou UPDATE OF quilometragem. A alteração isolada de status de agendada para realizada não dispara esse trigger. Corrija e teste os dois caminhos.
- vw_situacao_manutencao usa CURRENT_DATE como base quando não há manutenção anterior nem data de aquisição. Nesse caso, o prazo avança a cada dia. Substitua por uma base persistente e confiável, com tratamento explícito dos dados anteriores.
- As chaves estrangeiras simples não garantem que manutenção e plano, diagnóstico e manutenção, ou foto e seu registro vinculado pertençam ao mesmo veículo. Reforce a integridade no banco com uma solução compatível com as regras de exclusão existentes, além das verificações na API.
- Não existe estrutura de recuperação de senha de uso único. Proponha a tabela e os índices necessários, incluindo consumo seguro sob concorrência.
- Não existe registro da data da leitura atual de quilometragem nem histórico específico dessas leituras. Acrescente o necessário para sustentar os indicadores e a correção de leituras.
- A placa tem unicidade por usuário, mas não normalização automática. E-mail já tem índice único em lower(email); verifique também o tratamento de espaços.
- Abastecimentos usam litros e valor_litro mesmo permitindo GNV. Resolva ou delimite explicitamente essa incompatibilidade de unidade sem perder dados existentes.
- Mantenha coerência nas restrições, views, triggers, migrations e modelos usados pelo backend. Não deixe a mesma regra implementada de maneiras contraditórias.

Antes de impor novas restrições, identifique dados antigos incompatíveis. Forneça um procedimento de correção que preserve os registros e não invente datas ou valores. Registre quais migrations já foram aplicadas, informe backup e a estratégia de recuperação em caso de falha.

INTERFACE E ARQUITETURA

- Siga o estilo do PDF: verde-petróleo, fundo claro, cartões, indicadores e navegação inferior com Início, Manutenção, Diagnóstico, Finanças e Mais.
- Use português do Brasil, reais e datas brasileiras. Documente o uso de America/Sao_Paulo nas regras de calendário; trate campos DATE sem deslocá-los acidentalmente por conversão de fuso.
- Implemente telas complementares para cadastro, edição, seleção, recuperação de senha, conta e demais fluxos ausentes no PDF, mantendo o mesmo padrão visual.
- Todos os botões devem executar ações reais. Inclua carregamento, lista vazia, validação, sucesso, erro, prevenção de envio duplicado e confirmação de ações destrutivas.
- Organize frontend e backend em pastas separadas, com nomes e responsabilidades claros. PostgreSQL deve ser acessado apenas pelo backend.
- Não coloque credenciais do banco, chaves privadas ou senhas de e-mail em variáveis públicas do frontend.
- Escolha versões compatíveis das dependências e inclua os arquivos de dependências e travamento de versões pertinentes. Evite complexidade que não seja necessária para este projeto.
- Se a escolha for PWA, diferencie instalação, cache e operação offline. Não prometa funcionamento offline ou sincronização sem implementá-los e testá-los; inicialmente, operações de dados podem exigir conexão. Não deixe dados privados de um usuário acessíveis pelo cache após logout ou troca de conta.

ENTREGAS POR ETAPAS

Após a decisão de plataforma, organize etapas que entreguem fluxos completos e integrados. Uma ordem possível é: estrutura e banco; autenticação e permissões; veículos e quilometragem; manutenções; diagnósticos; gastos e finanças; abastecimentos e consumo; projetos e fotos; histórico, dashboard e administração; revisão integrada. Você pode ajustar a ordem para respeitar dependências.

Em cada etapa:
- Informe o objetivo e o que ficará funcionando.
- Mostre a estrutura de pastas e o caminho de cada arquivo criado ou alterado.
- Entregue código completo dos arquivos da etapa. Não use reticências, pseudocódigo, funções vazias ou instruções como implemente o restante para uma funcionalidade prometida nessa etapa.
- Não reenvie arquivos sem alteração. Se houver muitos arquivos e seu ambiente permitir, forneça também um pacote para download com o código integral, sem substituir a explicação necessária para executar.
- Informe os comandos exatos para Windows, preferencialmente PowerShell, e a pasta em que cada comando deve ser executado. Se um comando exigir CMD, explique a diferença.
- Inclua dependências, .env.example sem segredos reais, configuração do PostgreSQL e README atualizado.
- Mostre como iniciar frontend e backend, acessar a aplicação, executar migrations e testar o que acabou de ser entregue, com resultado esperado.
- Atualize um quadro de concluído, em andamento e pendente. Ao parar por limite de resposta, pare entre arquivos completos e deixe um ponto claro para continuar.
- Não marque a etapa como validada apenas porque o código foi gerado. Diferencie código entregue, teste executado e validação ainda necessária no meu computador.

Explique como testar pelo celular e configurar o endereço da API. Distinga localhost do computador e do celular, descreva rede local, portas, firewall e configuração de origem quando aplicável. Explique os requisitos de HTTPS para os recursos escolhidos e as alternativas de teste compatíveis. O celular se conecta ao backend; ele não deve receber acesso direto ao PostgreSQL.

Use dados demonstrativos somente em carga opcional de desenvolvimento, separada das migrations e desativada por padrão. O sistema deve funcionar com banco vazio, sem depender dos exemplos do PDF.

Ao final, entregue o projeto completo e integrado, README do início ao fim, instruções de criação do primeiro administrador, configuração de e-mail e fotos, execução no Windows, acesso pelo celular e lista objetiva do que foi testado e do que depende do meu ambiente. Publicação em lojas ou contratação de hospedagem não fazem parte da execução automática deste pedido.

TESTES E CRITÉRIOS DE ACEITE

Faça testes significativos dos fluxos, permissões e cálculos. Os testes de integridade e integração do banco precisam usar PostgreSQL, pois SQLite não comprova o funcionamento dos domains, views e triggers deste SQL.

Cubra ao menos:
- Cadastro com e-mail equivalente em maiúsculas/minúsculas, tentativa de escolher admin e conta desativada com sessão anteriormente válida.
- Dois usuários padrão e um administrador; tentativas de acessar ou alterar veículo, registro, anotação, item e foto de outro usuário, inclusive por ID direto.
- Tentativas de vincular registros de veículos diferentes, inclusive dois veículos do mesmo proprietário.
- Link de recuperação válido, expirado, reutilizado e consumido simultaneamente; alteração de senha e invalidação prevista das sessões.
- Quilometragem antiga que não reduz a atual; manutenção agendada que não aumenta a atual; transição isolada para realizada; correção de leitura e recálculo.
- Plano sem manutenção anterior, prazos por km e tempo, limite atingido primeiro e faixas de 1.000 km/30 dias.
- Resolução de diagnóstico com manutenção e falha forçada que comprove rollback das duas operações.
- Totais sem duplicação, gasto pago/pendente, mudança de mês, arredondamento e despesas de projeto cancelado que devem permanecer contabilizadas.
- Consumo com dois cheios, parciais, dados insuficientes, registros históricos, mistura/troca de combustível e comparação etanol/gasolina sem percentual fixo.
- Custo por km com numerador e denominador do mesmo período, aquisição ausente e distância zero.
- Upload com formato ou tamanho inválido, acesso indevido a foto, troca de capa e vínculos do mesmo veículo.
- Orçamento de projeto ausente, zero e excedido; inativação de veículo preservando seu histórico; proteção do último administrador ativo.

Informe comandos executados, resultados obtidos e limitações reais do ambiente de teste. Se não puder executar algo, forneça o teste e diga claramente que ele ainda não foi executado. Não invente resultados nem declare os módulos totalmente funcionando sem validação.

Se eu enviar um erro durante o desenvolvimento, analise a mensagem e indique a correção no arquivo correspondente, preservando o que já funciona. Não reinicie o projeto sem necessidade.

Comece agora somente pela análise dos anexos, proposta das etapas e perguntas indispensáveis sobre a plataforma, conforme a seção da primeira resposta.
