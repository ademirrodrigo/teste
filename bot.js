const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
} = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');
const dayjs = require('dayjs');
const customParseFormat = require('dayjs/plugin/customParseFormat');
const {
  findOrCreateUser,
  addProduct,
  listProductsByUser,
  getExpiringProductsByUser,
  getExpiredProductsByUser,
  activateUserAccess,
} = require('./db');

dayjs.extend(customParseFormat);

// Estado simples em memória para guiar usuários com baixa familiaridade técnica.
// Chave = phone, valor = etapa atual do fluxo.
const userFlows = new Map();

function getMenuText() {
  return [
    '👋 *Bem-vindo ao Controle de Vencimentos*',
    '',
    'Digite o número da opção:',
    '1️⃣ Cadastrar produto',
    '2️⃣ Ver meus produtos',
    '3️⃣ Produtos vencendo (5 dias)',
    '4️⃣ Produtos vencidos',
    '',
    'Também aceito comandos rápidos:',
    '• menu',
    '• add,arroz,2026-04-10',
    '• list',
    '• expiring',
    '• expired',
  ].join('\n');
}

function getHelpText() {
  return [
    '🤖 *Como usar (bem simples):*',
    '1) Envie *1* para cadastrar produto',
    '2) Digite o nome do produto',
    '3) Digite a data de vencimento',
    '',
    'Exemplo de data:',
    '• 2026-12-30',
    '• 30/12/2026',
    '',
    'Para voltar ao início, envie: *menu*',
  ].join('\n');
}

function formatProductList(title, items) {
  if (!items.length) return `*${title}*\nNenhum produto encontrado.`;

  const lines = items.map((item, index) => {
    const date = dayjs(item.expiration_date).format('DD/MM/YYYY');
    return `${index + 1}. ${item.name} - vence em ${date}`;
  });

  return [`*${title}*`, ...lines].join('\n');
}

function parseDateToIso(dateText) {
  const clean = dateText.trim();
  const formats = ['YYYY-MM-DD', 'DD/MM/YYYY', 'D/M/YYYY'];

  for (const format of formats) {
    const parsed = dayjs(clean, format, true);
    if (parsed.isValid()) {
      return parsed.format('YYYY-MM-DD');
    }
  }

  return null;
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
      'Se quiser testar o placeholder de pagamento, envie: *pay*',
  });

  return false;
}

function clearUserFlow(phone) {
  userFlows.delete(phone);
}

async function startAddFlow(sock, remoteJid, phone) {
  userFlows.set(phone, { step: 'awaiting_name' });
  await sock.sendMessage(remoteJid, {
    text:
      '📝 Vamos cadastrar um produto.\n' +
      'Primeiro, me diga o *nome do produto*.\n' +
      'Exemplo: Leite Integral',
  });
}

async function handleFlowMessage(sock, remoteJid, phone, user, incomingText) {
  const flow = userFlows.get(phone);
  if (!flow) return false;

  if (flow.step === 'awaiting_name') {
    const productName = incomingText.trim();
    if (!productName) {
      await sock.sendMessage(remoteJid, { text: 'Digite um nome válido para o produto.' });
      return true;
    }

    userFlows.set(phone, { step: 'awaiting_date', productName });
    await sock.sendMessage(remoteJid, {
      text:
        `Perfeito! Produto: *${productName}*\n` +
        'Agora informe a data de vencimento.\n' +
        'Exemplos: *2026-12-30* ou *30/12/2026*',
    });
    return true;
  }

  if (flow.step === 'awaiting_date') {
    const isoDate = parseDateToIso(incomingText);
    if (!isoDate) {
      await sock.sendMessage(remoteJid, {
        text: 'Data inválida 😕\nTente no formato *YYYY-MM-DD* ou *DD/MM/YYYY*.',
      });
      return true;
    }

    await addProduct(user.id, flow.productName, isoDate);
    clearUserFlow(phone);

    await sock.sendMessage(remoteJid, {
      text:
        `✅ Produto *${flow.productName}* cadastrado!\n` +
        `📅 Vencimento: *${dayjs(isoDate).format('DD/MM/YYYY')}*\n\n` +
        'Envie *menu* para ver outras opções.',
    });
    return true;
  }

  clearUserFlow(phone);
  return false;
}

async function sendList(sock, remoteJid, user) {
  const products = await listProductsByUser(user.id);
  await sock.sendMessage(remoteJid, {
    text: formatProductList('📦 Seus produtos', products),
  });
}

async function sendExpiring(sock, remoteJid, user) {
  const products = await getExpiringProductsByUser(user.id, 5);
  await sock.sendMessage(remoteJid, {
    text: formatProductList('⏳ Vencendo em até 5 dias', products),
  });
}

async function sendExpired(sock, remoteJid, user) {
  const products = await getExpiredProductsByUser(user.id);
  await sock.sendMessage(remoteJid, {
    text: formatProductList('🚫 Produtos vencidos', products),
  });
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

    // Comandos sempre disponíveis (mesmo usuário inativo)
    if (['menu', 'oi', 'olá', 'ola', 'início', 'inicio'].includes(command)) {
      clearUserFlow(phone);
      await sock.sendMessage(remoteJid, { text: getMenuText() });
      return;
    }

    if (['ajuda', 'help'].includes(command)) {
      await sock.sendMessage(remoteJid, { text: getHelpText() });
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

    // Se usuário está em fluxo guiado, prioriza essa tratativa.
    const flowHandled = await handleFlowMessage(sock, remoteJid, phone, user, incoming);
    if (flowHandled) return;

    // Atalhos por número no menu
    if (command === '1') {
      await startAddFlow(sock, remoteJid, phone);
      return;
    }

    if (command === '2' || command === 'list' || command === 'listar') {
      await sendList(sock, remoteJid, user);
      return;
    }

    if (command === '3' || command === 'expiring' || command === 'vencendo') {
      await sendExpiring(sock, remoteJid, user);
      return;
    }

    if (command === '4' || command === 'expired' || command === 'vencidos') {
      await sendExpired(sock, remoteJid, user);
      return;
    }

    // Mantém comando técnico original para compatibilidade
    if (command.startsWith('add,')) {
      const parts = incoming.split(',');
      if (parts.length < 3) {
        await sock.sendMessage(remoteJid, {
          text: 'Formato inválido. Use: add,<nome>,<YYYY-MM-DD>',
        });
        return;
      }

      const name = parts[1].trim();
      const isoDate = parseDateToIso(parts[2]);

      if (!name) {
        await sock.sendMessage(remoteJid, { text: 'Informe o nome do produto.' });
        return;
      }

      if (!isoDate) {
        await sock.sendMessage(remoteJid, {
          text: 'Data inválida. Use YYYY-MM-DD ou DD/MM/YYYY.',
        });
        return;
      }

      await addProduct(user.id, name, isoDate);
      await sock.sendMessage(remoteJid, {
        text: `✅ Produto *${name}* salvo com vencimento em *${dayjs(isoDate).format('DD/MM/YYYY')}*.`,
      });
      return;
    }

    if (['cadastrar', 'adicionar', 'add'].includes(command)) {
      await startAddFlow(sock, remoteJid, phone);
      return;
    }

    await sock.sendMessage(remoteJid, {
      text:
        'Não entendi 😅\n' +
        'Envie *menu* para ver as opções ou *ajuda* para um passo a passo.',
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
