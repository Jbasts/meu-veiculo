---
name: etapa
description: Executa uma etapa do plano do Meu Veículo (0 a 10), seguindo requisitos.md e progresso.md, e termina com testes e instruções para a Paula.
argument-hint: "[número da etapa]"
disable-model-invocation: true
---

Execute a etapa $ARGUMENTS do projeto Meu Veículo. Se nenhum número foi informado, use a próxima etapa pendente de `docs/progresso.md` e diga qual é.

1. Releia `CLAUDE.md`, `docs/progresso.md`, `docs/decisoes.md` e as seções de `docs/requisitos.md` ligadas a esta etapa. Se a etapa anterior não estiver "validada", avise antes de começar e pergunte se a Paula quer seguir mesmo assim.
2. Etapa 0: faça somente a primeira resposta descrita em `docs/requisitos.md` ("REFERÊNCIAS E PRIMEIRA RESPOSTA"), usando também `docs/observacoes-anexos.md`. Não crie código; apenas atualize `docs/progresso.md` e `docs/decisoes.md` depois que ela responder.
3. Demais etapas: antes de escrever código, apresente em poucas linhas o objetivo, o que ficará funcionando e os arquivos que serão criados ou alterados. Depois implemente.
4. Entregue código completo: sem reticências, pseudocódigo, funções vazias ou "implemente o restante" para algo prometido nesta etapa.
5. Rode os testes da etapa contra o PostgreSQL de teste e a suíte das etapas anteriores. Corrija as falhas antes de encerrar. O que não puder ser executado aqui (celular, câmera, e-mail real, HTTPS), diga claramente e deixe o teste pronto.
6. Termine com:
   - o que ficou funcionando e o que ainda não;
   - árvore de pastas com os arquivos criados ou alterados;
   - comandos PowerShell exatos, com a pasta de cada um, para a Paula iniciar e testar, e o resultado esperado;
   - testes executados: comando, resumo da saída, quantos passaram e falharam;
   - o que ainda depende de validação no computador ou no celular dela.
7. Atualize `docs/progresso.md` (status "entregue" e registro da etapa), `docs/decisoes.md`, o `README.md` e a seção "Comandos do projeto" do `CLAUDE.md`.
8. Sugira uma mensagem de commit. Só faça o commit se a Paula autorizar. Pare aqui e espere a resposta dela.
