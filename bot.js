const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
} = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');
const dayjs = require('dayjs');
const {
  findOrCreateUser,
  addProduct,
  listProductsByUser,
  getExpiringProductsByUser,
  getExpiredProductsByUser,
  activateUserAccess,
} = require('./db');

function getMenuText() {
  return [
    '📦 *Menu - Controle de Vencimentos*',
    '1 - Add product',
    '2 - List products',
    '3 - Expiring soon',
    '4 - Expired',
    '',
    'Comandos rápidos:',
    '• menu',
    '• add,<nome>,<YYYY-MM-DD>',
    '• list',
    '• expiring',
    '• expired',
  ].join('\n');
}

function formatProductList(title, items) {
  if (!items.length) return `*${title}*\nNenhum produto encontrado.`;

  const lines = items.map((item, index) => {
    const date = dayjs(item.expiration_date).format('DD/MM/YYYY');
    return `${index + 1}. ${item.name} - ${date}`;
  });

  return [`*${title}*`, ...lines].join('\n');
}

function validateDate(dateText) {
  return dayjs(dateText, 'YYYY-MM-DD', true).isValid();
}

// Placeholder do MVP para lógica de pagamento Pix.
// Aqui você pode integrar um gateway de pagamento real no futuro.
async function processPixActivation(user) {
  console.log(`[PAYMENT] Placeholder Pix para usuário ${user.phone}`);
  // Exemplo de ativação fictícia por 30 dias:
  // const expirationAccessDate = dayjs().add(30, 'day').format('YYYY-MM-DD');
  // await activateUserAccess(user.id, expirationAccessDate);
  return false;
}

async function ensureActiveOrBlock(sock, remoteJid, user) {
  if (user.active === 1) return true;

  await sock.sendMessage(remoteJid, {
    text:
      '⚠️ Seu acesso está inativo.\n' +
      'Para liberar, finalize o pagamento Pix.\n' +
      'Quando quiser testar a rotina de pagamento, envie: *pay*',
  });

  return false;
}

async function handleIncomingMessage(sock, msg) {
  try {
    const remoteJid = msg.key.remoteJid;
    if (!remoteJid || !remoteJid.endsWith('@s.whatsapp.net')) return;

    const text =
      msg.message?.conversation ||
      msg.message?.extendedTextMessage?.text ||
      msg.message?.imageMessage?.caption ||
      '';

    const incoming = text.trim();
    if (!incoming) return;

    const phone = remoteJid.split('@')[0];
    const user = await findOrCreateUser(phone);
    const command = incoming.toLowerCase();

    console.log(`[BOT] Mensagem de ${phone}: ${incoming}`);

    if (command === 'menu' || command === '1' || command === '2' || command === '3' || command === '4') {
      await sock.sendMessage(remoteJid, { text: getMenuText() });
      return;
    }

    if (command === 'pay') {
      const activated = await processPixActivation(user);
      if (activated) {
        const expirationAccessDate = dayjs().add(30, 'day').format('YYYY-MM-DD');
        await activateUserAccess(user.id, expirationAccessDate);
        await sock.sendMessage(remoteJid, { text: '✅ Pagamento confirmado. Acesso liberado!' });
      } else {
        await sock.sendMessage(remoteJid, {
          text: '🧪 Placeholder Pix: integração de pagamento ainda não conectada.',
        });
      }
      return;
    }

    const canUse = await ensureActiveOrBlock(sock, remoteJid, user);
    if (!canUse) return;

    if (command.startsWith('add,')) {
      const parts = incoming.split(',');
      if (parts.length < 3) {
        await sock.sendMessage(remoteJid, {
          text: 'Formato inválido. Use: add,<nome>,<YYYY-MM-DD>',
        });
        return;
      }

      const name = parts[1].trim();
      const expirationDate = parts[2].trim();

      if (!name) {
        await sock.sendMessage(remoteJid, { text: 'Informe o nome do produto.' });
        return;
      }

      if (!validateDate(expirationDate)) {
        await sock.sendMessage(remoteJid, {
          text: 'Data inválida. Use o formato YYYY-MM-DD.',
        });
        return;
      }

      await addProduct(user.id, name, expirationDate);
      await sock.sendMessage(remoteJid, {
        text: `✅ Produto *${name}* salvo com vencimento em *${expirationDate}*.`,
      });
      return;
    }

    if (command === 'list') {
      const products = await listProductsByUser(user.id);
      await sock.sendMessage(remoteJid, {
        text: formatProductList('Todos os produtos', products),
      });
      return;
    }

    if (command === 'expiring') {
      const products = await getExpiringProductsByUser(user.id, 5);
      await sock.sendMessage(remoteJid, {
        text: formatProductList('Vencendo em até 5 dias', products),
      });
      return;
    }

    if (command === 'expired') {
      const products = await getExpiredProductsByUser(user.id);
      await sock.sendMessage(remoteJid, {
        text: formatProductList('Produtos vencidos', products),
      });
      return;
    }

    await sock.sendMessage(remoteJid, {
      text: 'Comando não reconhecido. Envie *menu* para ver as opções.',
    });
  } catch (error) {
    console.error('[BOT] Erro ao processar mensagem:', error);
  }
}

async function connectWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState('./auth_info');

  const sock = makeWASocket({
    auth: state,
    printQRInTerminal: false,
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', (update) => {
    const { connection, qr, lastDisconnect } = update;

    if (qr) {
      console.log('[BOT] Escaneie o QR Code abaixo:');
      qrcode.generate(qr, { small: true });
    }

    if (connection === 'open') {
      console.log('[BOT] WhatsApp conectado com sucesso!');
    }

    if (connection === 'close') {
      const shouldReconnect =
        lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;

      console.log('[BOT] Conexão encerrada. Reconectar?', shouldReconnect);
      if (shouldReconnect) connectWhatsApp();
    }
  });

  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;
    for (const msg of messages) {
      if (!msg.key.fromMe) {
        await handleIncomingMessage(sock, msg);
      }
    }
  });

  return sock;
}

module.exports = {
  connectWhatsApp,
};
