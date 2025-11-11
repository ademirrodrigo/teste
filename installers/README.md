# Sequência de arquivos de instalação

1. `01_windows_installer.ps1`
2. `02_linux_installer.sh`

Cada script é independente e pode ser enviado diretamente ao responsável pela instalação na plataforma correspondente.

- Ambos os scripts geram um arquivo `.env` com a chave secreta e as credenciais iniciais.
- Para enviar o conjunto completo com manual e frontend, execute `python tools/create_install_bundle.py` na raiz do projeto e encaminhe o arquivo `dist/bpo_instalacao.zip`.
