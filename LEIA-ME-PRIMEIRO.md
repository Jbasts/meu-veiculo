# Comece aqui: Meu Veículo com o Claude Code

Este kit prepara a pasta do projeto para o Claude Code. Quando você abrir o Claude Code dentro dela, ele lê o `CLAUDE.md` automaticamente e já sabe o que é o projeto, onde estão as telas, o banco e o seu pedido completo, como deve trabalhar com você e quais regras não pode quebrar. Assim você não precisa colar o prompt enorme a cada sessão.

## O que tem na pasta

| Arquivo | Para que serve |
|---|---|
| `CLAUDE.md` | Instruções permanentes do projeto. O Claude Code lê sozinho a cada sessão. |
| `docs/requisitos.md` | Seu pedido original, sem alterações. É a fonte da verdade. |
| `docs/telas-mobile.pdf` | As telas do Figma. |
| `database/original/meu_veiculo_banco.sql` | Seu SQL original. Fica intocado; mudanças viram migrations novas. |
| `docs/observacoes-anexos.md` | Pontos extras que notei no SQL e no PDF, para o Claude confirmar na etapa 0. |
| `docs/progresso.md` | Quadro das etapas (pendente, em andamento, entregue, validada). |
| `docs/decisoes.md` | Registro das decisões técnicas e dos motivos. |
| `.claude/skills/etapa/` | Cria o comando `/etapa`, que executa uma etapa do plano. |
| `.claude/skills/erro/` | Cria o comando `/erro`, para colar um erro e pedir a correção. |

## 1. Instale os programas (uma vez só)

- **Plano do Claude**: o Claude Code exige conta Pro, Max, Team, Enterprise ou Console. O plano gratuito não inclui.
- **VS Code**: o editor.
- **Git for Windows**: recomendado. Guarda versões do projeto (dá para desfazer mudanças) e permite ao Claude Code usar o terminal Bash.
- **Node.js** (versão LTS): roda o frontend.
- **Python** (versão estável atual): roda o backend.
- **PostgreSQL** (instalador oficial para Windows): durante a instalação, anote a senha do usuário `postgres`. Você vai precisar dela.

Na etapa 1, o Claude Code confere as versões instaladas e avisa se faltar algo.

## 2. Instale o Claude Code

Abra o **PowerShell** (o prompt começa com `PS C:\`) e rode:

```powershell
irm https://claude.ai/install.ps1 | iex
```

Feche o PowerShell, abra de novo e confira:

```powershell
claude --version
```

Deve aparecer um número de versão. Se aparecer "não é reconhecido", feche e abra o terminal mais uma vez; se continuar, veja https://code.claude.com/docs/en/troubleshoot-install. O comando `claude doctor` também mostra um diagnóstico da instalação.

Opcional: no VS Code, em Extensões, instale a extensão **Claude Code** para usar num painel ao lado do código.

## 3. Prepare a pasta do projeto

Extraia o zip em um caminho curto, sem acentos e fora de pastas sincronizadas pelo OneDrive (Documentos e Área de Trabalho costumam ser sincronizadas e atrapalham pastas como `node_modules`). Sugestão: `C:\projetos\meu-veiculo`.

Confira que o `CLAUDE.md` ficou direto dentro de `meu-veiculo` (às vezes o Windows cria `meu-veiculo\meu-veiculo`).

No PowerShell:

```powershell
cd C:\projetos\meu-veiculo
git init
git add .
git commit -m "Kit inicial: requisitos, telas e banco"
```

Se o Git pedir sua identidade, rode uma vez e repita o commit:

```powershell
git config --global user.name "Paula"
git config --global user.email "seu@email.com"
```

## 4. Abra o projeto e inicie o Claude Code

```powershell
cd C:\projetos\meu-veiculo
code .
```

No VS Code, abra o terminal (menu Terminal > Novo Terminal) e digite:

```powershell
claude
```

Na primeira vez, o navegador abre para você entrar na sua conta. Depois, o Claude Code pergunta se você confia na pasta: confirme.

## 5. Etapa 0: análise e escolha da plataforma

Digite:

```
/etapa 0
```

O Claude Code vai ler os anexos e responder exatamente o que seu pedido define para a primeira resposta: resumo do sistema, inconsistências do banco, comparação entre web/PWA e aplicativo, stack recomendada e as perguntas sobre plataforma e celulares. Nenhum código é criado nessa etapa. Responda às perguntas dele.

## 6. O ciclo de cada etapa

1. Digite `/etapa` (ele pega a próxima pendente) ou `/etapa 3` para uma etapa específica.
2. O Claude Code escreve o código, cria o banco de teste e roda os testes. Antes de executar comandos, ele pede permissão: leia o que vai rodar. Se não entender, pergunte "o que esse comando faz?" antes de aprovar.
3. No fim, ele mostra os comandos para você iniciar e testar. Rode e veja no navegador.
4. Deu certo? Escreva "etapa validada, pode fazer o commit". Deu erro? Digite `/erro` e cole a mensagem completa.
5. Antes de começar a etapa seguinte, digite `/clear` para limpar a conversa. Nada se perde: a continuidade fica no `CLAUDE.md`, no `progresso.md` e no `decisoes.md`.

## 7. Se algo der errado

- Para desfazer as últimas mudanças do Claude Code, use `/rewind` ou peça: "desfaça o que você mudou nesta etapa".
- Como você faz commit ao fim de cada etapa validada, sempre dá para voltar a um ponto que funcionava. Peça ajuda ao Claude antes de usar comandos do Git que descartam alterações.
- O que ele não consegue fazer sozinho: instalar o PostgreSQL com a sua senha, abrir o app no seu celular, tirar fotos com a câmera e confirmar a chegada de um e-mail real. Nesses pontos, ele deixa o teste pronto e você executa.
