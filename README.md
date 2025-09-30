# Pilates Control – Micro-SaaS local para estúdios de pilates

Pilates Control é um sistema multiempresas e multiusuários focado na rotina administrativa de estúdios e profissionais autônomos de pilates. Ele roda em ambiente local (localhost) ou em VPS própria (ex.: Contabo), oferecendo ferramentas para agenda, controle financeiro, lembretes e geração do arquivo do **Carnê-Leão / Livro Caixa Digital da Receita Federal (LCDPR)**.

## Principais recursos

- **Multiempresas**: cada estúdio possui cadastro e dados isolados. Super administradores podem alternar entre estúdios para suporte.
- **Multiusuários**: convide instrutores e equipe administrativa com perfis distintos (proprietário, administrativo, instrutor).
- **Agenda inteligente**: cadastro de aulas, turmas, lotação e matrículas, com visão rápida das próximas sessões.
- **Lembretes e confirmações**: registre envios por e-mail ou WhatsApp (manual ou com integrações externas) e mantenha histórico dos contatos.
- **Financeiro simplificado**: acompanhe mensalidades, pacotes e aulas avulsas, receba alertas de pendências e visualize recebimentos do mês.
- **Carnê-Leão / LCDPR**: gere o arquivo `.txt` no layout oficial da Receita Federal com os pagamentos marcados como pagos, pronto para importar no Livro Caixa Digital.
- **Pronto para VPS**: pode ser executado localmente com o servidor embutido ou publicado com Gunicorn + Nginx em VPS próprias (Contabo, DigitalOcean, etc.).

## Stack utilizada

- **Backend**: Python 3, Flask, SQLAlchemy.
- **Autenticação**: Flask-Login com senhas criptografadas.
- **Banco de dados**: SQLite por padrão (arquivo local). Compatível com PostgreSQL/MySQL via variável `DATABASE_URL`.
- **Frontend**: HTML5 + CSS responsivo com templates Jinja2.

## Pré-requisitos

- Python 3.9 ou superior.
- Acesso ao terminal/PowerShell para instalar dependências e executar comandos.

## Instalação local (Linux/macOS)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=main.py
export FLASK_ENV=development  # opcional para recarregar automaticamente
flask init-db
flask run
```

## Instalação local (Windows PowerShell)

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:FLASK_APP = 'main.py'
$env:FLASK_ENV = 'development'   # opcional
flask init-db
flask run
```

A aplicação ficará disponível em `http://127.0.0.1:5000`.

### Variáveis de ambiente importantes

| Variável        | Descrição                                                                 |
|-----------------|---------------------------------------------------------------------------|
| `SECRET_KEY`    | Chave para sessões e cookies. Defina uma string segura em produção.       |
| `DATABASE_URL`  | URL de conexão alternativa (ex.: `postgresql://user:pass@host/dbname`).   |

## Comandos de linha de comando (Flask CLI)

| Comando                   | Função                                                                                  |
|---------------------------|-----------------------------------------------------------------------------------------|
| `flask init-db`           | Cria as tabelas no banco configurado.                                                   |
| `flask create-superuser`  | Cria um usuário global (`superadmin`) para suporte multiempresas.                       |
| `flask seed-demo`         | Popula dados fictícios para testar rapidamente (opcional).                              |

## Fluxo básico de uso

1. **Cadastro do estúdio**: acesse `/register`, informe dados do responsável e crie a conta.
2. **Convite da equipe**: na aba **Usuários**, crie logins para instrutores/administrativo.
3. **Cadastro de alunos e instrutores**: insira contatos, CPF/CNPJ e observações.
4. **Agenda**: crie aulas, defina lotação e matricule alunos.
5. **Lembretes**: registre envios (manual, e-mail, WhatsApp) e acompanhe o histórico.
6. **Financeiro**: registre cobranças, marque pagamentos e acompanhe pendências.
7. **Carnê-Leão / LCDPR**: em **Carnê-Leão**, selecione o ano-base e faça o download do arquivo.

> 💡 Para que o LCDPR seja aceito pelo programa da Receita Federal, mantenha CPF dos alunos, datas de pagamento e status “Pago” atualizados. O arquivo gerado segue o layout oficial (registros `0000`, `0001`, `0100`, `0200`, `0500`, `9900`).

## Implantação em VPS Contabo (exemplo)

1. **Preparação do servidor**
   ```bash
   sudo apt update && sudo apt install -y python3-venv python3-pip nginx
   mkdir -p /opt/pilates-control
   cd /opt/pilates-control
   python3 -m venv venv
   source venv/bin/activate
   git clone <seu-repositorio> .
   pip install -r requirements.txt
   export FLASK_APP=main.py
   flask init-db
   flask create-superuser
   ```

2. **Serviço com Gunicorn** (`/etc/systemd/system/pilates.service`)
   ```ini
   [Unit]
   Description=Pilates Control
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/opt/pilates-control
   Environment="FLASK_APP=main.py" "SECRET_KEY=<sua-chave>"
   ExecStart=/opt/pilates-control/venv/bin/gunicorn -b 127.0.0.1:8000 main:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now pilates
   ```

3. **Proxy reverso Nginx** (`/etc/nginx/sites-available/pilates`)
   ```nginx
   server {
       listen 80;
       server_name sua-api.seudominio.com.br;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

   ```bash
   sudo ln -s /etc/nginx/sites-available/pilates /etc/nginx/sites-enabled/pilates
   sudo nginx -t
   sudo systemctl restart nginx
   ```

4. **Banco de dados externo (opcional)**
   - Ajuste `DATABASE_URL` para PostgreSQL/MySQL gerenciado (contêiner, RDS, etc.).
   - Execute `flask init-db` novamente após configurar a nova conexão.

5. **Backups**
   - **SQLite**: copie o arquivo `pilates.db` periodicamente.
   - **PostgreSQL/MySQL**: utilize `pg_dump`/`mysqldump` com cron.

## Roadmap sugerido

- Integração com APIs de WhatsApp/SMS para envio automático.
- Dashboard avançado com gráficos semanais.
- Portal do aluno para autoagendamento.
- Integração contábil com emissão de NFS-e.

## Suporte

Em caso de dúvidas ou sugestões, abra uma issue ou entre em contato com a equipe responsável pela implantação.
