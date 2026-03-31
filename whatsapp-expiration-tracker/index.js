const express = require('express');
const { connectWhatsApp, sendMessage, generatePixPayment } = require('./bot');
const { initCronJobs, triggerManualAlert } = require('./cron');
const db = require('./db');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

/**
 * Root endpoint - Health check
 */
app.get('/', (req, res) => {
  res.json({
    status: 'ok',
    service: 'WhatsApp Expiration Tracker',
    version: '1.0.0',
    timestamp: new Date().toISOString()
  });
});

/**
 * API: Get user info by phone
 */
app.get('/api/user/:phone', (req, res) => {
  try {
    const { phone } = req.params;
    const user = db.getUserByPhone(phone);
    
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    res.json({
      success: true,
      user: {
        id: user.id,
        phone: user.phone,
        active: user.active === 1,
        expiration_access_date: user.expiration_access_date,
        created_at: user.created_at
      }
    });
  } catch (error) {
    console.error('[API ERROR] /api/user/:phone:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * API: Get products for a user
 */
app.get('/api/products/:phone', (req, res) => {
  try {
    const { phone } = req.params;
    const products = db.getProducts(phone);
    
    res.json({
      success: true,
      count: products.length,
      products
    });
  } catch (error) {
    console.error('[API ERROR] /api/products/:phone:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * API: Add product via HTTP (alternative to WhatsApp)
 */
app.post('/api/product', (req, res) => {
  try {
    const { phone, name, expiration_date } = req.body;
    
    if (!phone || !name || !expiration_date) {
      return res.status(400).json({ 
        error: 'Missing required fields: phone, name, expiration_date' 
      });
    }
    
    const product = db.addProduct(phone, name, expiration_date);
    
    res.json({
      success: true,
      message: 'Product added successfully',
      product
    });
  } catch (error) {
    console.error('[API ERROR] POST /api/product:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * API: Generate Pix payment code (placeholder)
 */
app.post('/api/payment/pix', (req, res) => {
  try {
    const { phone } = req.body;
    
    if (!phone) {
      return res.status(400).json({ error: 'Phone number required' });
    }
    
    const paymentInfo = generatePixPayment(phone);
    
    res.json({
      success: true,
      payment: paymentInfo,
      instructions: [
        '1. Open your banking app',
        '2. Choose "Pix" option',
        '3. Scan the QR code or copy the Pix code',
        '4. Complete the payment',
        '5. Your access will be activated automatically'
      ]
    });
  } catch (error) {
    console.error('[API ERROR] POST /api/payment/pix:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * API: Activate user (simulate payment confirmation)
 * In production, this would be called by payment gateway webhook
 */
app.post('/api/payment/activate', (req, res) => {
  try {
    const { phone, expiration_date } = req.body;
    
    if (!phone) {
      return res.status(400).json({ error: 'Phone number required' });
    }
    
    // Default to 30 days if no expiration date provided
    const expDate = expiration_date || new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0];
    
    db.activateUser(phone, expDate);
    
    res.json({
      success: true,
      message: 'User activated successfully',
      expiration_date: expDate
    });
  } catch (error) {
    console.error('[API ERROR] POST /api/payment/activate:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * API: Deactivate user
 */
app.post('/api/user/deactivate', (req, res) => {
  try {
    const { phone } = req.body;
    
    if (!phone) {
      return res.status(400).json({ error: 'Phone number required' });
    }
    
    db.deactivateUser(phone);
    
    res.json({
      success: true,
      message: 'User deactivated successfully'
    });
  } catch (error) {
    console.error('[API ERROR] POST /api/user/deactivate:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * API: Trigger manual alert check (for testing)
 */
app.post('/api/alerts/trigger', async (req, res) => {
  try {
    console.log('[API] Manual alert trigger requested');
    await triggerManualAlert();
    
    res.json({
      success: true,
      message: 'Alert check completed'
    });
  } catch (error) {
    console.error('[API ERROR] POST /api/alerts/trigger:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * Start the server
 */
async function startServer() {
  console.log('\n========================================');
  console.log('📦 WhatsApp Expiration Tracker MVP');
  console.log('========================================\n');
  
  // Initialize database (already done in db.js require)
  console.log('[INIT] Database initialized ✓');
  
  // Start Express server
  app.listen(PORT, () => {
    console.log(`[HTTP] Server running on port ${PORT}`);
    console.log(`[HTTP] Health check: http://localhost:${PORT}/\n`);
  });
  
  // Connect to WhatsApp
  console.log('[INIT] Connecting to WhatsApp...\n');
  await connectWhatsApp();
  
  // Initialize cron jobs
  initCronJobs();
  
  console.log('\n========================================');
  console.log('✅ System ready!');
  console.log('========================================');
  console.log('\n📱 WhatsApp: Waiting for messages...');
  console.log('🕐 Cron: Daily alerts at 8:00 AM');
  console.log('🌐 API: http://localhost:' + PORT);
  console.log('\n----------------------------------------\n');
}

// Handle uncaught errors
process.on('uncaughtException', (error) => {
  console.error('\n[CRITICAL] Uncaught Exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('\n[CRITICAL] Unhandled Rejection at:', promise, 'reason:', reason);
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n\n[SHUTDOWN] Closing server...');
  process.exit(0);
});

// Start the application
startServer().catch((error) => {
  console.error('[FATAL] Failed to start server:', error);
  process.exit(1);
});
