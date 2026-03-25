const cron = require('node-cron');
const dayjs = require('dayjs');
const { getUsersForAlerts, getProductsForUserAlerts } = require('./db');

function normalizePhoneToJid(phone) {
  return `${phone}@s.whatsapp.net`;
}

function buildAlertMessage(productName, expirationDate, diffDays) {
  const formattedDate = dayjs(expirationDate).format('DD/MM/YYYY');

  if (diffDays === 5) {
    return `🔔 Alerta: *${productName}* vence em 5 dias (${formattedDate}).`;
  }

  if (diffDays === 3) {
    return `⚠️ Atenção: *${productName}* vence em 3 dias (${formattedDate}).`;
  }

  if (diffDays === 0) {
    return `⛔ Produto vencido hoje: *${productName}* (${formattedDate}).`;
  }

  return null;
}

async function runExpirationAlerts(sock) {
  try {
    console.log('[CRON] Iniciando verificação de vencimentos...');

    const users = await getUsersForAlerts();
    const today = dayjs().startOf('day');

    for (const user of users) {
      const products = await getProductsForUserAlerts(user.id);
      const jid = normalizePhoneToJid(user.phone);

      for (const product of products) {
        const expiration = dayjs(product.expiration_date).startOf('day');
        const diffDays = expiration.diff(today, 'day');

        const message = buildAlertMessage(product.name, product.expiration_date, diffDays);
        if (!message) continue;

        await sock.sendMessage(jid, { text: message });
        console.log(`[CRON] Alerta enviado para ${user.phone} - ${product.name}`);
      }
    }

    console.log('[CRON] Verificação finalizada.');
  } catch (error) {
    console.error('[CRON] Erro ao executar alertas:', error);
  }
}

function startDailyCron(sock) {
  // Todo dia às 08:00 (timezone do servidor)
  cron.schedule('0 8 * * *', async () => {
    await runExpirationAlerts(sock);
  });

  console.log('[CRON] Agendamento diário ativado para 08:00.');
}

module.exports = {
  startDailyCron,
  runExpirationAlerts,
};
