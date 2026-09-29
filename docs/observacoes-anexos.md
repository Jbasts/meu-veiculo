# Observações adicionais sobre os anexos

Pontos notados numa leitura prévia do SQL e do PDF, além dos que `requisitos.md` já lista. Confirme cada um na etapa 0 (podem estar incompletos ou errados) e trate os procedentes nas etapas correspondentes.

## Banco (`database/original/meu_veiculo_banco.sql`)

1. `vw_situacao_manutencao` também usa `COALESCE(u.quilometragem, v.km_aquisicao, 0)`. Sem manutenção anterior e sem km de aquisição, a base vira 0 km, ou seja, uma leitura inventada, o que `requisitos.md` proíbe (além do problema do `CURRENT_DATE` já apontado lá).
2. A mesma view só cobre planos (`plano_manutencao`). Manutenções `agendada` avulsas e os campos manuais `proxima_data`/`proxima_km` de `manutencao` ficam de fora, e há duas fontes possíveis para a "próxima" de um plano. Risco de alerta ausente ou duplicado na aba Pendentes.
3. `diagnostico.manutencao_id` usa `ON DELETE SET NULL`: apagar a manutenção deixa o diagnóstico `resolvido` sem vínculo. Nada impede vincular uma manutenção `agendada`.
4. `atualizar_km_veiculo()` só aumenta a quilometragem. Corrigir um km digitado a mais num abastecimento não reduz `veiculo.quilometragem`; é preciso o procedimento explícito de correção pedido em `requisitos.md`.
5. `abastecimento.valor_total` não é conferido com `litros × valor_litro`.
6. `projeto` não liga `status = 'concluido'` a `data_conclusao` (diferente de `diagnostico`, que exige `data_resolucao`).
7. `gasto.pago` tem padrão `TRUE` e não exige `data_vencimento` quando pendente. `vw_historico` usa `gasto.data` para posicionar o gasto no tempo, o que se conecta à decisão sobre `data_pagamento`.
8. Não existe coluna de tipo de veículo (carro, moto...). A menção a "tipos de veículo" em `requisitos.md` provavelmente se refere aos valores `hibrido` e `eletrico` de `tipo_combustivel`; confirmar com a Paula. Nada impede registrar diesel num carro flex ou abastecimento num elétrico.

## Telas (`docs/telas-mobile.pdf`)

1. Combustível: 38,5 L × R$ 4,29 = R$ 165,165, e a tela mostra R$ 165,17. Bom caso de teste de arredondamento.
2. "Etanol ou gasolina?": 7,9 ÷ 11,3 ≈ 0,70, então os "70%" da tela coincidem com o cálculo por consumo e não devem ser um valor fixo. O preço do etanol sobre o da gasolina dá 4,29 ÷ 6,25 ≈ 0,686, os "69%" da tela.
3. A sequência de abastecimentos do exemplo (08/09 gasolina parcial, 15/09 etanol cheio, 20/09 gasolina cheio) mostra justamente ciclos de transição: o intervalo que termina em 20/09 rodou com o etanol de 15/09 e seria atribuído à gasolina. É o erro que `requisitos.md` pede para evitar; bom cenário de teste.
4. Nova manutenção: os campos "Garantia até" e "Ou até (km)" sugerem que `garantia_km` é um limite absoluto do hodômetro. Definir e manter consistente no formulário, banco e alertas.
5. A tela inicial agrupa "Outros" (R$ 30,00), que em Finanças aparece como "Estacionamento". Definir quais categorias a tela inicial mostra e como agrupa o restante.
6. Placas do exemplo: "ABC-1234" (com hífen) e "BRA2E19" (padrão Mercosul, sem hífen). Casos reais para a normalização.
