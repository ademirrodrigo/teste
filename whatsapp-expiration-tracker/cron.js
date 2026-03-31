const cron = require('node-cron');
const db = require('./db');
const { sendMessage } = require('./bot');

/**
 * Format date for display
 * @param {string} dateStr - Date string (YYYY-MM-DD)
 * @returns {string} Formatted date
 */
function formatDate(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric' 
  });
}

/**
 * Send expiration alerts to all users
 * Checks for products expiring in 5 days, 3 days, and already expired
 */
async function sendExpirationAlerts() {
  console.log('\n[CRON] Running expiration alert check...');
  
  try {
    let totalAlerts = 0;
    
    // Check products expiring in 5 days
    console.log('[CRON] Checking products expiring in 5 days...');
    const expiring5Days = db.getProductsExpiringInDays(5);
    
    for (const product of expiring5Days) {
      const jid = `${product.phone}@s.whatsapp.net`;
      const message = `🟡 *Expiration Alert* 🟡\n\n` +
        `Your product *${product.name}* will expire in *5 days*!\n\n` +
        `📅 Expiration date: ${formatDate(product.expiration_date)}\n\n` +
        `Check your products by sending *list* to the bot.`;
      
      await sendMessage(jid, message);
      totalAlerts++;
    }
    
    // Check products expiring in 3 days
    console.log('[CRON] Checking products expiring in 3 days...');
    const expiring3Days = db.getProductsExpiringInDays(3);
    
    for (const product of expiring3Days) {
      const jid = `${product.phone}@s.whatsapp.net`;
      const message = `🟠 *Urgent Expiration Alert* 🟠\n\n` +
        `Your product *${product.name}* will expire in *3 days*!\n\n` +
        `📅 Expiration date: ${formatDate(product.expiration_date)}\n\n` +
        `⚠️ Please use it soon or dispose of it properly.`;
      
      await sendMessage(jid, message);
      totalAlerts++;
    }
    
    // Check already expired products
    console.log('[CRON] Checking expired products...');
    const expiredProducts = db.getAllExpiredProducts();
    
    for (const product of expiredProducts) {
      const jid = `${product.phone}@s.whatsapp.net`;
      const message = `🔴 *PRODUCT EXPIRED* 🔴\n\n` +
        `Your product *${product.name}* has *EXPIRED*!\n\n` +
        `📅 Expiration date: ${formatDate(product.expiration_date)}\n\n` +
        `⚠️ Do not consume! Please dispose of it properly.`;
      
      await sendMessage(jid, message);
      totalAlerts++;
    }
    
    console.log(`[CRON] Alert check completed. Total alerts sent: ${totalAlerts}`);
    
  } catch (error) {
    console.error('[CRON] Error sending alerts:', error);
  }
}

/**
 * Initialize cron jobs
 * - Daily at 8:00 AM: Send expiration alerts
 */
function initCronJobs() {
  console.log('[CRON] Initializing scheduled jobs...');
  
  // Run every day at 8:00 AM
  // Cron format: second minute hour day month weekday
  const dailyJob = cron.schedule('0 0 8 * * *', async () => {
    console.log('\n[CRON] === Daily Alert Job Started ===');
    await sendExpirationAlerts();
    console.log('[CRON] === Daily Alert Job Completed ===\n');
  }, {
    timezone: 'America/Sao_Paulo', // Adjust to your timezone
    scheduled: true
  });
  
  console.log('[CRON] Daily alert job scheduled for 8:00 AM');
  
  // For testing: Run every minute (commented out by default)
  // Uncomment the following lines to test the cron job immediately
  /*
  const testJob = cron.schedule('* * * * * *', async () => {
    console.log('\n[CRON] === Test Alert Job ===');
    await sendExpirationAlerts();
  }, {
    scheduled: false // Disabled by default
  });
  */
  
  return dailyJob;
}

/**
 * Manual trigger for testing
 * Can be called from index.js to test alerts immediately
 */
async function triggerManualAlert() {
  console.log('\n[MANUAL] Triggering manual alert check...');
  await sendExpirationAlerts();
}

module.exports = {
  initCronJobs,
  triggerManualAlert,
  sendExpirationAlerts
};
