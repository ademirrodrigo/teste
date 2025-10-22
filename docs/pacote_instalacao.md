# Pacote completo para instalação do BPO Financeiro

Este guia reúne todos os arquivos necessários para enviar ao cliente (ou equipe interna) na ordem correta e inclui um manual visual para facilitar a implantação. Combine o conteúdo com o script `tools/create_install_bundle.py` para gerar um arquivo `.zip` pronto para distribuição.

## Como gerar o pacote .zip

```bash
python tools/create_install_bundle.py
```

O comando cria `dist/bpo_instalacao.zip` com todos os itens listados abaixo. Para escolher outro destino use `-o`:

```bash
python tools/create_install_bundle.py -o /caminho/para/pacote.zip
```

Se desejar enviar apenas os instaladores sem a interface web, acrescente `--skip-frontend`.

## Conteúdo do pacote

1. `README.md` – visão geral do sistema, requisitos e comandos principais.
2. `requirements.txt` – lista das dependências Python necessárias.
3. `installers/01_windows_installer.ps1` – script PowerShell para Windows 11.
4. `installers/02_linux_installer.sh` – script bash para Linux ou VPS.
5. `installers/README.md` – instruções rápidas sobre os instaladores.
6. `docs/manual_canva.md` – manual em formato Canva (um slide por seção).
7. `docs/pacote_instalacao.md` – este guia para acompanhar o envio.
8. `frontend/` – pastas `index.html`, `styles.css` e `main.js` para quem prefere servir a interface estaticamente.
9. `MANIFEST.json` – índice automático gerado pelo script com todos os arquivos incluídos.

> **Dica:** compartilhe o `.zip` com clientes ou com a equipe do escritório pelo canal de sua preferência (e-mail, Drive, etc.).

## Sequência sugerida para envio ao cliente final

1. **Anexe o arquivo `.zip`** gerado pelo script.
2. **Copie a mensagem abaixo**, ajustando apenas os campos em destaque:

   ```
   Olá, [Nome do cliente]!

   Segue o pacote com tudo o que você precisa para começar a usar o nosso BPO Financeiro.
   Passos recomendados:
   1. Descompacte o arquivo em uma pasta simples, como C:\BPO ou /home/usuario/bpo.
   2. Abra o manual "docs/manual_canva.md" para ver os slides passo a passo.
   3. Execute o instalador apropriado:
      - Windows 11: installers/01_windows_installer.ps1
      - Linux / VPS: installers/02_linux_installer.sh
   4. Guarde os dados de acesso exibidos ao final da instalação.
   5. Acesse http://localhost:8000 e personalize a senha imediatamente.

   Qualquer dúvida, nossa equipe está disponível para ajudar.
   ```

3. **Inclua o manual visual** caso o cliente prefira receber diretamente em Canva: basta importar `docs/manual_canva.md` para o Canva ou outro editor de apresentações.
4. **Agende uma call de acompanhamento** para revisar o primeiro acesso e garantir que os relatórios estejam claros para o cliente.

## Checklist pós-instalação

- [ ] Trocar a senha padrão do administrador exibida pelo instalador.
- [ ] Validar importação de um extrato (CSV, Excel ou OFX) para conferir as categorias automáticas.
- [ ] Gerar um relatório de Fluxo de Caixa e exportar para PDF/Excel.
- [ ] Revisar o painel administrativo do escritório e confirmar se as empresas aparecem corretamente.

## Perguntas frequentes

### O cliente não consegue executar scripts no Windows
Peça para abrir o PowerShell como Administrador e rodar:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

Depois disso o instalador deve executar normalmente. Caso a restrição continue, envie apenas o comando manual descrito no README (`python -m venv`, `pip install`, etc.).

### O instalador não encontra o Python
Inclua o link oficial (https://www.python.org/downloads/) na comunicação e oriente a instalar a versão 3.9 ou superior. Após a instalação, peça para abrir um novo terminal e executar o script novamente.

### É possível atualizar o sistema depois de enviado?
Sim. Envie um novo `.zip` gerado com `create_install_bundle.py`. O cliente pode descompactar por cima da pasta existente ou executar o instalador novamente para atualizar dependências e interface.

---

Com este pacote você tem um kit completo para distribuir o BPO Financeiro de forma profissional, mantendo os passos organizados e fáceis de seguir.
