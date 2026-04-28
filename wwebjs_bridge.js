/**
 * Bridge HTTP simples para envio de mensagens via whatsapp-web.js.
 *
 * Uso:
 *   1) npm install
 *   2) node wwebjs_bridge.js
 *   3) Escaneie o QR code no terminal (primeiro login)
 *   4) Python chama POST /send-message
 */

const express = require('express');
const qrcode = require('qrcode-terminal');
const { Client, LocalAuth } = require('whatsapp-web.js');

const PORT = Number(process.env.WWEBJS_PORT || 3000);
const AUTH_TOKEN = process.env.WWEBJS_TOKEN || '';

const app = express();
app.use(express.json());

const client = new Client({
  authStrategy: new LocalAuth({ clientId: 'cobrancas-mvp' }),
  puppeteer: {
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  },
});

let ready = false;

client.on('qr', (qr) => {
  console.log('\nEscaneie o QR code para logar no WhatsApp:');
  qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
  ready = true;
  console.log('wwebjs pronto para envio.');
});

client.on('authenticated', () => {
  console.log('WhatsApp autenticado.');
});

client.on('auth_failure', (msg) => {
  ready = false;
  console.error('Falha de autenticação:', msg);
});

client.on('disconnected', (reason) => {
  ready = false;
  console.error('WhatsApp desconectado:', reason);
});

function authMiddleware(req, res, next) {
  if (!AUTH_TOKEN) {
    return next();
  }

  const authHeader = req.headers.authorization || '';
  const expected = `Bearer ${AUTH_TOKEN}`;
  if (authHeader !== expected) {
    return res.status(401).json({ ok: false, error: 'unauthorized' });
  }
  return next();
}

app.get('/health', (_req, res) => {
  res.json({ ok: true, ready });
});

app.post('/send-message', authMiddleware, async (req, res) => {
  const { phone, message } = req.body;
  if (!phone || !message) {
    return res.status(400).json({ ok: false, error: 'phone and message are required' });
  }

  if (!ready) {
    return res.status(503).json({ ok: false, error: 'whatsapp client is not ready yet' });
  }

  const chatId = `${String(phone).replace(/\D/g, '')}@c.us`;
  try {
    const result = await client.sendMessage(chatId, String(message));
    return res.json({ ok: true, id: result.id?._serialized || null });
  } catch (err) {
    return res.status(500).json({ ok: false, error: String(err.message || err) });
  }
});

app.listen(PORT, () => {
  console.log(`Bridge wwebjs ouvindo na porta ${PORT}`);
});

client.initialize();
