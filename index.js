const express = require('express');
const { initDb } = require('./db');
const { connectWhatsApp } = require('./bot');
const { startDailyCron } = require('./cron');

const PORT = process.env.PORT || 3000;

async function bootstrap() {
  try {
    await initDb();

    const app = express();
    app.use(express.json());

    app.get('/health', (_req, res) => {
      res.json({ status: 'ok', message: 'MVP WhatsApp rodando' });
    });

    app.listen(PORT, () => {
      console.log(`[SERVER] API rodando na porta ${PORT}`);
    });

    const sock = await connectWhatsApp();
    startDailyCron(sock);

    console.log('[SERVER] Sistema iniciado com sucesso.');
  } catch (error) {
    console.error('[SERVER] Erro ao iniciar aplicação:', error);
    process.exit(1);
  }
}

bootstrap();
