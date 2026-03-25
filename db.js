const path = require('path');
const sqlite3 = require('sqlite3');
const { open } = require('sqlite');

let db;

async function initDb() {
  if (db) return db;

  db = await open({
    filename: path.join(__dirname, 'mvp.sqlite'),
    driver: sqlite3.Database,
  });

  await db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      phone TEXT NOT NULL UNIQUE,
      active INTEGER NOT NULL DEFAULT 1,
      expiration_access_date TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
  `);

  await db.exec(`
    CREATE TABLE IF NOT EXISTS products (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      expiration_date TEXT NOT NULL,
      user_id INTEGER NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      FOREIGN KEY(user_id) REFERENCES users(id)
    );
  `);

  console.log('[DB] SQLite pronto em', path.join(__dirname, 'mvp.sqlite'));
  return db;
}

async function findUserByPhone(phone) {
  const database = await initDb();
  return database.get('SELECT * FROM users WHERE phone = ?', [phone]);
}

async function createUser(phone) {
  const database = await initDb();
  await database.run(
    'INSERT INTO users (phone, active, expiration_access_date) VALUES (?, 1, NULL)',
    [phone]
  );
  return findUserByPhone(phone);
}

async function findOrCreateUser(phone) {
  let user = await findUserByPhone(phone);
  if (!user) {
    user = await createUser(phone);
    console.log(`[DB] Novo usuário criado: ${phone}`);
  }
  return user;
}

async function listProductsByUser(userId) {
  const database = await initDb();
  return database.all(
    'SELECT id, name, expiration_date FROM products WHERE user_id = ? ORDER BY expiration_date ASC',
    [userId]
  );
}

async function addProduct(userId, name, expirationDate) {
  const database = await initDb();
  const result = await database.run(
    'INSERT INTO products (name, expiration_date, user_id) VALUES (?, ?, ?)',
    [name, expirationDate, userId]
  );
  return result.lastID;
}

async function getExpiringProductsByUser(userId, daysAhead = 5) {
  const database = await initDb();
  return database.all(
    `SELECT id, name, expiration_date
     FROM products
     WHERE user_id = ?
       AND date(expiration_date) BETWEEN date('now') AND date('now', '+' || ? || ' day')
     ORDER BY expiration_date ASC`,
    [userId, daysAhead]
  );
}

async function getExpiredProductsByUser(userId) {
  const database = await initDb();
  return database.all(
    `SELECT id, name, expiration_date
     FROM products
     WHERE user_id = ?
       AND date(expiration_date) < date('now')
     ORDER BY expiration_date ASC`,
    [userId]
  );
}

async function getUsersForAlerts() {
  const database = await initDb();
  return database.all('SELECT * FROM users WHERE active = 1');
}

async function getProductsForUserAlerts(userId) {
  const database = await initDb();
  return database.all(
    `SELECT id, name, expiration_date
     FROM products
     WHERE user_id = ?
     ORDER BY expiration_date ASC`,
    [userId]
  );
}

async function activateUserAccess(userId, expirationAccessDate) {
  const database = await initDb();
  await database.run(
    'UPDATE users SET active = 1, expiration_access_date = ? WHERE id = ?',
    [expirationAccessDate, userId]
  );
}

module.exports = {
  initDb,
  findOrCreateUser,
  listProductsByUser,
  addProduct,
  getExpiringProductsByUser,
  getExpiredProductsByUser,
  getUsersForAlerts,
  getProductsForUserAlerts,
  activateUserAccess,
};
