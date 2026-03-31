const Database = require('better-sqlite3');
const path = require('path');

// Initialize SQLite database
const dbPath = path.join(__dirname, 'expiration_tracker.db');
const db = new Database(dbPath);

// Enable foreign keys
db.pragma('foreign_keys = ON');

// Create users table
db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT UNIQUE NOT NULL,
    active INTEGER DEFAULT 1,
    expiration_access_date TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

// Create products table
db.exec(`
  CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    expiration_date TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
  )
`);

// Create indexes for better query performance
db.exec(`
  CREATE INDEX IF NOT EXISTS idx_products_user_id ON products(user_id);
  CREATE INDEX IF NOT EXISTS idx_products_expiration_date ON products(expiration_date);
  CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
`);

/**
 * Get or create a user by phone number
 * @param {string} phone - User's phone number
 * @returns {Object} User object
 */
function getUserByPhone(phone) {
  const stmt = db.prepare('SELECT * FROM users WHERE phone = ?');
  let user = stmt.get(phone);
  
  if (!user) {
    // Create new user if doesn't exist
    const insertStmt = db.prepare('INSERT INTO users (phone) VALUES (?)');
    insertStmt.run(phone);
    user = getUserByPhone(phone);
  }
  
  return user;
}

/**
 * Check if user is active
 * @param {string} phone - User's phone number
 * @returns {boolean} True if user is active
 */
function isUserActive(phone) {
  const user = getUserByPhone(phone);
  return user && user.active === 1;
}

/**
 * Add a product for a user
 * @param {string} phone - User's phone number
 * @param {string} name - Product name
 * @param {string} expirationDate - Expiration date (YYYY-MM-DD)
 * @returns {Object} Created product
 */
function addProduct(phone, name, expirationDate) {
  const user = getUserByPhone(phone);
  const stmt = db.prepare(`
    INSERT INTO products (name, expiration_date, user_id)
    VALUES (?, ?, ?)
  `);
  const result = stmt.run(name, expirationDate, user.id);
  
  return {
    id: result.lastInsertRowid,
    name,
    expiration_date: expirationDate,
    user_id: user.id
  };
}

/**
 * Get all products for a user
 * @param {string} phone - User's phone number
 * @returns {Array} List of products
 */
function getProducts(phone) {
  const user = getUserByPhone(phone);
  const stmt = db.prepare(`
    SELECT * FROM products 
    WHERE user_id = ? 
    ORDER BY expiration_date ASC
  `);
  return stmt.all(user.id);
}

/**
 * Get products expiring within N days
 * @param {string} phone - User's phone number
 * @param {number} days - Number of days
 * @returns {Array} List of expiring products
 */
function getExpiringProducts(phone, days = 5) {
  const user = getUserByPhone(phone);
  const today = new Date().toISOString().split('T')[0];
  const futureDate = new Date();
  futureDate.setDate(futureDate.getDate() + days);
  const futureDateStr = futureDate.toISOString().split('T')[0];
  
  const stmt = db.prepare(`
    SELECT * FROM products 
    WHERE user_id = ? 
    AND expiration_date >= ? 
    AND expiration_date <= ?
    ORDER BY expiration_date ASC
  `);
  
  return stmt.all(user.id, today, futureDateStr);
}

/**
 * Get expired products for a user
 * @param {string} phone - User's phone number
 * @returns {Array} List of expired products
 */
function getExpiredProducts(phone) {
  const user = getUserByPhone(phone);
  const today = new Date().toISOString().split('T')[0];
  
  const stmt = db.prepare(`
    SELECT * FROM products 
    WHERE user_id = ? 
    AND expiration_date < ?
    ORDER BY expiration_date ASC
  `);
  
  return stmt.all(user.id, today);
}

/**
 * Get all active users
 * @returns {Array} List of active users
 */
function getAllActiveUsers() {
  const stmt = db.prepare('SELECT * FROM users WHERE active = 1');
  return stmt.all();
}

/**
 * Get products expiring on a specific date for all users
 * @param {number} daysBefore - Days before expiration (e.g., 5 for 5 days before)
 * @returns {Array} List of products with user info
 */
function getProductsExpiringInDays(daysBefore) {
  const targetDate = new Date();
  targetDate.setDate(targetDate.getDate() + daysBefore);
  const targetDateStr = targetDate.toISOString().split('T')[0];
  
  const stmt = db.prepare(`
    SELECT p.*, u.phone 
    FROM products p
    JOIN users u ON p.user_id = u.id
    WHERE p.expiration_date = ? AND u.active = 1
  `);
  
  return stmt.all(targetDateStr);
}

/**
 * Get all expired products for active users
 * @returns {Array} List of expired products with user info
 */
function getAllExpiredProducts() {
  const today = new Date().toISOString().split('T')[0];
  
  const stmt = db.prepare(`
    SELECT p.*, u.phone 
    FROM products p
    JOIN users u ON p.user_id = u.id
    WHERE p.expiration_date < ? AND u.active = 1
  `);
  
  return stmt.all(today);
}

/**
 * Deactivate a user (for payment logic)
 * @param {string} phone - User's phone number
 */
function deactivateUser(phone) {
  const stmt = db.prepare('UPDATE users SET active = 0 WHERE phone = ?');
  stmt.run(phone);
}

/**
 * Activate a user (after payment)
 * @param {string} phone - User's phone number
 * @param {string} expirationDate - Access expiration date
 */
function activateUser(phone, expirationDate) {
  const stmt = db.prepare('UPDATE users SET active = 1, expiration_access_date = ? WHERE phone = ?');
  stmt.run(expirationDate, phone);
}

module.exports = {
  db,
  getUserByPhone,
  isUserActive,
  addProduct,
  getProducts,
  getExpiringProducts,
  getExpiredProducts,
  getAllActiveUsers,
  getProductsExpiringInDays,
  getAllExpiredProducts,
  deactivateUser,
  activateUser
};
