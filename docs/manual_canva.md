# Manual Visual do BPO Financeiro

> **Formato sugerido para Canva:** cada seção abaixo corresponde a um slide. Use os blocos de texto como títulos e descrições, adicionando imagens ou ícones conforme desejar.

---

## Slide 1 — Capa inspiradora
- **Título:** "BPO Financeiro Simples"
- **Subtítulo:** "Controle financeiro claro para seu escritório e seus clientes"
- **Destaques:** multiempresas, relatórios visuais, acesso seguro

---

## Slide 2 — Visão geral do sistema
- **Bloco 1:** "Tudo em um só lugar" — painel administrativo para o contador com visão geral de cada empresa
- **Bloco 2:** "Clientes com acesso fácil" — cada empresa enxerga apenas seus próprios dados
- **Bloco 3:** "Relatórios amigáveis" — fluxo de caixa, resultados e listas de contas em linguagem simples

---

## Slide 3 — Checklist pré-instalação
- Windows 11 ou Linux com acesso a internet
- Python 3.9 ou superior instalado
- Porta 8000 liberada na máquina ou servidor
- Arquivos do repositório baixados (zip ou git clone)

---

## Slide 4 — Instalação Windows 11
1. Abra o **PowerShell como Administrador**
2. Acesse a pasta do projeto: `cd CAMINHO\DO\PROJETO`
3. Entre na pasta `installers`: `cd installers`
4. Permita scripts temporariamente: `Set-ExecutionPolicy -Scope Process Bypass`
5. Execute: `./01_windows_installer.ps1`
6. Aguarde a criação do ambiente virtual e a instalação automática das dependências

> **Dica visual:** destaque o passo final com um callout "Acesse http://localhost:8000".

---

## Slide 5 — Instalação Windows (opções extras)
- `-Host 127.0.0.1` para restringir o acesso à própria máquina
- `-Port 9000` se precisar mudar a porta padrão
- `-SkipRun` para somente instalar e iniciar depois manualmente

> **Como iniciar depois:** `\.venv\Scripts\uvicorn.exe bpo_app.main:app --host 0.0.0.0 --port 8000`

---

## Slide 6 — Instalação VPS Linux (Contábil)
1. Conecte-se via SSH ao servidor VPS
2. Acesse a pasta do projeto: `cd /caminho/do/projeto`
3. Entre na pasta `installers`
4. Dê permissão de execução: `chmod +x 02_linux_installer.sh`
5. Rode o script: `./02_linux_installer.sh`
6. O servidor inicia automaticamente em `http://IP_DA_VPS:8000`

> **Tipografia sugerida:** utilize cores verdes e ícones de terminal para reforçar o fluxo técnico.

---

## Slide 7 — Instalação Linux (opções extras)
- `./02_linux_installer.sh --skip-run` para instalar sem iniciar
- `./02_linux_installer.sh --host 127.0.0.1 --port 9000` para personalizar rede
- Os instaladores criam automaticamente um arquivo `.env` com chave secreta e credenciais iniciais (personalize depois do login).

---

## Slide 8 — Primeiro acesso do escritório
- Abra `http://localhost:8000`
- Use o e-mail e a senha exibidos pelo instalador (ou definidos no arquivo `.env`).
- Assim que entrar, troque a senha do administrador em **Configurações > Segurança**.
- Cadastre o primeiro cliente em **Empresas > Nova Empresa**

---

## Slide 9 — Convidando clientes
1. Acesse a empresa recém-criada
2. Clique em **Equipe da Empresa > Convidar usuário**
3. Informe nome, e-mail e defina o perfil "Cliente"
4. Compartilhe o link de acesso com o cliente

> **Sugestão Canva:** usar mockups de e-mail ou chat para ilustrar o convite.

---

## Slide 10 — Cadastro de contas e categorias
- Use **Finanças > Contas bancárias** para adicionar bancos ou carteiras
- Crie categorias intuitivas (ex: "Vendas online", "Pagamentos fornecedores")
- Defina palavras-chave para ajudar na classificação automática

---

## Slide 11 — Importando extratos
1. Vá em **Finanças > Importar extrato**
2. Selecione um arquivo CSV, Excel (.xlsx) ou OFX
3. Confirme a empresa e a conta bancária
4. Revise as sugestões de categoria antes de salvar

---

## Slide 12 — Lançamentos manuais
- Clique em **Finanças > Novo lançamento**
- Informe se é **Entrada** ou **Saída**
- Preencha valores, data, descrição amigável e categoria
- Anexe notas ou comprovantes para registrar justificativas

---

## Slide 13 — Relatórios que encantam
- **Destaques financeiros:** resumo das entradas, saídas e saldo projetado
- **Fluxo de caixa:** visão por período com gráfico simples
- **Resultado (DRE simplificada):** linguagem sem jargões contábeis
- **Contas a pagar/receber:** lista filtrável e exportável

---

## Slide 14 — Exportações
- Botão **Baixar Excel** disponível em cada relatório
- Botão **Gerar PDF** para compartilhar com diretoria ou investidores
- Sugestão: inclua o logotipo do cliente antes de enviar

---

## Slide 15 — Comunicação com o contador
- Use o quadro **Mensagens rápidas** no painel para enviar solicitações
- Registre comentários em cada lançamento para histórico
- Ative notificações por e-mail para avisar quando houver novidades

---

## Slide 16 — Boas práticas de segurança
- Troque as credenciais padrão imediatamente
- Utilize senhas fortes e exclusivas
- Restrinja o acesso por IP na VPS quando possível
- Faça backup periódico do arquivo `bpo_app.db`

---

## Slide 17 — Próximos passos sugeridos
- Personalize o visual no Canva com as cores do escritório
- Crie vídeos curtos de demonstração usando os slides como roteiro
- Planeje treinamentos rápidos com clientes estratégicos

---

## Slide 18 — Contatos e suporte
- **Equipe interna:** acesse o painel e use o chat interno para dúvidas
- **E-mail de suporte:** suporte@seuescritorio.com.br
- **Atualizações:** acompanhe novas versões no repositório oficial

---

> **Fim do manual.** Personalize os slides à vontade para deixar o material com a identidade visual do escritório.
