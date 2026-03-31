const { 
  default: makeWASocket,
  DisconnectReason,
  useMultiFileAuthState 
} = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');
const db = require('./db');

let sock;

/**
 * Format phone number from WhatsApp ID
 * @param {string} jid - WhatsApp JID (e.g., 5511999999999@s.whatsapp.net)
 * @returns {string} Phone number
 */
function formatPhone(jid) {
  return jid.split('@')[0];
}

/**
 * Send a text message via WhatsApp
 * @param {string} to - Recipient JID
 * @param {string} message - Message text
 */
async function sendMessage(to, message) {
  try {
    await sock.sendMessage(to, { text: message });
    console.log(`[SENT] To ${to}: ${message.substring(0, 50)}...`);
  } catch (error) {
    console.error(`[ERROR] Failed to send message to ${to}:`, error.message);
  }
}

/**
 * Show main menu
 * @returns {string} Menu text
 */
function getMenu() {
  return `📦 *Product Expiration Tracker*

Choose an option:

1️⃣ - Add product
2️⃣ - List products
3️⃣ - Expiring soon (5 days)
4️⃣ - Expired products

*Commands:*
• Add: add,<name>,<YYYY-MM-DD>
  Example: add,Milk,2025-04-15
• List: list
• Expiring: expiring
• Expired: expired
• Menu: menu

Reply with the number or type the command!`;
}

/**
 * Handle "add" command
 * @param {string} phone - User's phone number
 * @param {string} args - Command arguments (name,date)
 * @returns {string} Response message
 */
function handleAddCommand(phone, args) {
  try {
    const parts = args.split(',');
    
    if (parts.length < 2) {
      return '❌ Invalid format!\n\nUse: add,<name>,<YYYY-MM-DD>\nExample: add,Milk,2025-04-15';
    }
    
    const name = parts[0].trim();
    const dateStr = parts[1].trim();
    
    // Validate date format (YYYY-MM-DD)
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(dateStr)) {
      return '❌ Invalid date format!\n\nUse YYYY-MM-DD (e.g., 2025-04-15)';
    }
    
    // Validate date is valid
    const dateObj = new Date(dateStr);
    if (isNaN(dateObj.getTime())) {
      return '❌ Invalid date!\n\nMake sure the date is valid.';
    }
    
    // Add product to database
    const product = db.addProduct(phone, name, dateStr);
    
    return `✅ Product added successfully!\n\n📦 *${name}*\n📅 Expires: ${dateStr}`;
  } catch (error) {
    console.error('[ERROR] handleAddCommand:', error);
    return '❌ Error adding product. Please try again.';
  }
}

/**
 * Handle "list" command
 * @param {string} phone - User's phone number
 * @returns {string} Response message
 */
function handleListCommand(phone) {
  try {
    const products = db.getProducts(phone);
    
    if (products.length === 0) {
      return '📭 No products registered yet.\n\nUse *add,<name>,<date>* to add one!';
    }
    
    let message = `📦 *Your Products* (${products.length})\n\n`;
    
    products.forEach((p, index) => {
      const expDate = new Date(p.expiration_date);
      const today = new Date();
      const diffTime = expDate - today;
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      let status = '';
      if (diffDays < 0) {
        status = ' 🔴 EXPIRED';
      } else if (diffDays <= 5) {
        status = ' 🟡 EXPIRING SOON';
      } else {
        status = ' 🟢 OK';
      }
      
      message += `${index + 1}. *${p.name}*\n   📅 ${p.expiration_date}${status}\n\n`;
    });
    
    return message.trim();
  } catch (error) {
    console.error('[ERROR] handleListCommand:', error);
    return '❌ Error listing products. Please try again.';
  }
}

/**
 * Handle "expiring" command
 * @param {string} phone - User's phone number
 * @returns {string} Response message
 */
function handleExpiringCommand(phone) {
  try {
    const products = db.getExpiringProducts(phone, 5);
    
    if (products.length === 0) {
      return '✅ No products expiring in the next 5 days!';
    }
    
    let message = `🟡 *Expiring Soon* (${products.length})\n\n`;
    
    products.forEach((p, index) => {
      const expDate = new Date(p.expiration_date);
      const today = new Date();
      const diffTime = expDate - today;
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      message += `${index + 1}. *${p.name}*\n   📅 ${p.expiration_date}\n   ⏰ ${diffDays} day(s) left\n\n`;
    });
    
    return message.trim();
  } catch (error) {
    console.error('[ERROR] handleExpiringCommand:', error);
    return '❌ Error checking expiring products. Please try again.';
  }
}

/**
 * Handle "expired" command
 * @param {string} phone - User's phone number
 * @returns {string} Response message
 */
function handleExpiredCommand(phone) {
  try {
    const products = db.getExpiredProducts(phone);
    
    if (products.length === 0) {
      return '✅ No expired products!';
    }
    
    let message = `🔴 *Expired Products* (${products.length})\n\n`;
    
    products.forEach((p, index) => {
      const expDate = new Date(p.expiration_date);
      const today = new Date();
      const diffTime = today - expDate;
      const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
      
      message += `${index + 1}. *${p.name}*\n   📅 Expired: ${p.expiration_date}\n   ⚠️ ${diffDays} day(s) ago\n\n`;
    });
    
    return message.trim();
  } catch (error) {
    console.error('[ERROR] handleExpiredCommand:', error);
    return '❌ Error checking expired products. Please try again.';
  }
}

/**
 * Process incoming message
 * @param {string} phone - User's phone number
 * @param {string} message - Message text
 * @param {string} jid - User's JID
 */
async function processMessage(phone, message, jid) {
  try {
    // Get or create user
    const user = db.getUserByPhone(phone);
    console.log(`[USER] ${phone} - Active: ${user.active === 1}`);
    
    // Check if user is active (payment logic)
    if (user.active === 0) {
      await sendMessage(jid, '⚠️ *Account Inactive*\n\nYour access has expired.\n\nTo reactivate, please complete the payment.\n\nContact support for more info.');
      return;
    }
    
    const lowerMsg = message.toLowerCase().trim();
    
    // Handle commands
    if (lowerMsg === 'menu' || lowerMsg === '1') {
      await sendMessage(jid, getMenu());
    } 
    else if (lowerMsg === '2' || lowerMsg === 'list') {
      const response = handleListCommand(phone);
      await sendMessage(jid, response);
    }
    else if (lowerMsg === '3' || lowerMsg === 'expiring') {
      const response = handleExpiringCommand(phone);
      await sendMessage(jid, response);
    }
    else if (lowerMsg === '4' || lowerMsg === 'expired') {
      const response = handleExpiredCommand(phone);
      await sendMessage(jid, response);
    }
    else if (lowerMsg.startsWith('add,')) {
      const args = message.substring(4); // Remove 'add,' prefix
      const response = handleAddCommand(phone, args);
      await sendMessage(jid, response);
    }
    else {
      // Unknown command - show menu
      await sendMessage(jid, `🤔 I didn't understand that command.\n\n${getMenu()}`);
    }
    
  } catch (error) {
    console.error('[ERROR] processMessage:', error);
    await sendMessage(jid, '❌ An error occurred. Please try again later.');
  }
}

/**
 * Initialize WhatsApp connection
 */
async function connectWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState('auth_info');
  
  sock = makeWASocket({
    auth: state,
    printQRInTerminal: false
  });
  
  // Show QR code for authentication
  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;
    
    if (qr) {
      console.log('\n📱 Scan the QR code below with WhatsApp:\n');
      qrcode.generate(qr, { small: true });
    }
    
    if (connection === 'close') {
      const shouldReconnect = (lastDisconnect.error)?.output?.statusCode !== DisconnectReason.loggedOut;
      console.log('[CONNECTION] Closed. Reconnecting:', shouldReconnect);
      
      if (shouldReconnect) {
        await connectWhatsApp();
      }
    } else if (connection === 'open') {
      console.log('\n✅ WhatsApp connected successfully!\n');
    }
  });
  
  // Save credentials
  sock.ev.on('creds.update', saveCreds);
  
  // Handle incoming messages
  sock.ev.on('messages.upsert', async (m) => {
    const message = m.messages[0];
    
    // Ignore messages without text
    if (!message.message?.conversation && !message.message?.extendedTextMessage) {
      return;
    }
    
    // Get message content
    const text = message.message?.conversation || message.message?.extendedTextMessage?.text;
    
    // Ignore messages from bot itself
    if (!text || message.key.fromMe) {
      return;
    }
    
    const jid = message.key.remoteJid;
    const phone = formatPhone(jid);
    
    console.log(`[RECEIVED] From ${phone}: ${text}`);
    
    // Process the message
    await processMessage(phone, text, jid);
  });
}

/**
 * Placeholder function for Pix payment activation
 * In production, integrate with actual payment gateway
 * @param {string} phone - User's phone number
 * @returns {Object} Payment info
 */
function generatePixPayment(phone) {
  // This is a placeholder - in production, integrate with actual payment API
  return {
    pix_code: 'PLACEHOLDER_PIX_CODE_' + phone,
    amount: 9.90,
    description: 'Monthly subscription - Product Expiration Tracker',
    expiration: new Date(Date.now() + 86400000).toISOString() // 24 hours
  };
}

module.exports = {
  connectWhatsApp,
  sendMessage,
  getMenu,
  generatePixPayment
};
