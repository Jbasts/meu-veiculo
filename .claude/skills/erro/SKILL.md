---
name: erro
description: Analisa e corrige um erro do Meu Veículo (terminal, navegador, celular ou testes) sem desfazer o que já funciona. Use quando a Paula colar uma mensagem de erro ou disser que algo não funcionou.
argument-hint: "[mensagem de erro ou descrição do problema]"
---

A Paula encontrou um problema: $ARGUMENTS

Se a mensagem acima estiver vazia ou incompleta, peça para ela colar a saída completa e dizer qual comando rodou e em qual pasta.

1. Identifique onde o erro acontece (backend, frontend, banco, rede ou ambiente Windows) e explique a causa provável em linguagem simples.
2. Reproduza o erro quando possível antes de mudar código.
3. Corrija no arquivo correspondente com a menor mudança segura. Não reinicie nem reestruture o projeto.
4. Rode os testes afetados e a suíte relacionada para confirmar a correção e verificar que nada quebrou.
5. Responda com: causa, arquivos alterados, o que mudou, o comando para ela confirmar e o resultado esperado.
6. Se a causa for do ambiente (PATH, porta ocupada, firewall, serviço do PostgreSQL parado, política de execução do PowerShell, celular em outra rede), explique como resolver no Windows passo a passo.
7. Se a correção mudar uma decisão ou comando, atualize `docs/decisoes.md`, o `README.md` ou o `CLAUDE.md`.
