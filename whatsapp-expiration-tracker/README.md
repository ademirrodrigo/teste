# WhatsApp Product Expiration Tracker - MVP

A simple WhatsApp-based system for tracking product expiration dates. Users interact exclusively via WhatsApp to register products and receive automatic alerts before expiration.

## Features

- **User Registration**: Automatic user creation by phone number
- **Product Management**: Add, list, and track products with expiration dates
- **Automatic Alerts**: Daily cron job sends alerts at 8 AM for:
  - Products expiring in 5 days
  - Products expiring in 3 days
  - Already expired products
- **Payment System**: Simple active/inactive user status (Pix payment placeholder)
- **REST API**: Optional HTTP endpoints for integration

## Requirements

- Node.js 16+ 
- npm or yarn
- A WhatsApp account (for bot authentication)

## Installation

```bash
# Navigate to project directory
cd whatsapp-expiration-tracker

# Install dependencies
npm install

# Start the server
node index.js
```

## First Run

1. Run `node index.js`
2. Scan the QR code displayed in terminal with your WhatsApp mobile app
3. Once connected, the bot is ready to receive messages

## WhatsApp Commands

### Main Menu
Send `menu` or `1` to see available options

### Add Product
```
add,<product_name>,<YYYY-MM-DD>
```
Example: `add,Milk,2025-04-15`

### List Products
Send `list` or `2`

### Check Expiring Soon (5 days)
Send `expiring` or `3`

### Check Expired Products
Send `expired` or `4`

## REST API Endpoints

### Health Check
```
GET /
```

### Get User Info
```
GET /api/user/:phone
```

### Get User Products
```
GET /api/products/:phone
```

### Add Product (HTTP)
```
POST /api/product
Content-Type: application/json

{
  "phone": "5511999999999",
  "name": "Milk",
  "expiration_date": "2025-04-15"
}
```

### Generate Pix Payment (Placeholder)
```
POST /api/payment/pix
Content-Type: application/json

{
  "phone": "5511999999999"
}
```

### Activate User (Payment Confirmation)
```
POST /api/payment/activate
Content-Type: application/json

{
  "phone": "5511999999999",
  "expiration_date": "2025-12-31"
}
```

### Trigger Manual Alert (Testing)
```
POST /api/alerts/trigger
```

## Database

SQLite database file (`expiration_tracker.db`) is created automatically in the project root.

### Tables

**users**
- id: Primary key
- phone: Unique phone number
- active: Status (0 = inactive, 1 = active)
- expiration_access_date: Access expiration date
- created_at: Registration timestamp

**products**
- id: Primary key
- name: Product name
- expiration_date: Expiration date (YYYY-MM-DD)
- user_id: Foreign key to users
- created_at: Creation timestamp

## File Structure

```
whatsapp-expiration-tracker/
├── index.js          # Main server file (Express + initialization)
├── bot.js            # WhatsApp logic (Baileys)
├── db.js             # Database operations (SQLite)
├── cron.js           # Scheduled jobs (alerts)
├── package.json      # Dependencies
└── README.md         # This file
```

## Configuration

### Timezone
Edit `cron.js` to change the timezone for daily alerts:
```javascript
timezone: 'America/Sao_Paulo' // Change to your timezone
```

### Port
Set environment variable or default (3000):
```bash
export PORT=3000
```

## Payment Logic (MVP)

The system includes a simple payment placeholder:

1. Users start as `active = 1` by default
2. If `active = 0`, user cannot use the bot
3. `generatePixPayment()` function returns placeholder payment info
4. In production, integrate with actual payment gateway (Mercado Pago, Stripe, etc.)

## Testing

### Test with WhatsApp
1. Send `menu` to the bot number
2. Try adding a product: `add,Test Product,2025-04-20`
3. List products: `list`

### Test Cron Job Manually
```bash
curl -X POST http://localhost:3000/api/alerts/trigger
```

### Test API
```bash
# Add product via API
curl -X POST http://localhost:3000/api/product \
  -H "Content-Type: application/json" \
  -d '{"phone":"5511999999999","name":"Test","expiration_date":"2025-05-01"}'

# Get products
curl http://localhost:3000/api/products/5511999999999
```

## Logs

The system prints detailed logs:
- `[RECEIVED]` - Incoming WhatsApp messages
- `[SENT]` - Outgoing messages
- `[USER]` - User activity
- `[CRON]` - Scheduled job execution
- `[API]` - HTTP requests
- `[ERROR]` - Errors

## Troubleshooting

### QR Code not showing
- Make sure you're running in a terminal that supports ASCII output
- Check if `qrcode-terminal` is installed

### WhatsApp connection fails
- Ensure stable internet connection
- Try logging out from WhatsApp Web on other devices
- Delete `auth_info` folder and restart

### Database errors
- Check file permissions in project directory
- Delete `expiration_tracker.db` to reset database

## Production Deployment

For production use:

1. **Environment Variables**: Store sensitive data in `.env` file
2. **Process Manager**: Use PM2 or similar
   ```bash
   npm install -g pm2
   pm2 start index.js --name expiration-bot
   ```
3. **Database Backup**: Regularly backup `expiration_tracker.db`
4. **Payment Integration**: Replace placeholder with real payment gateway
5. **Monitoring**: Add error tracking (Sentry, etc.)

## License

MIT License - Free for personal and commercial use

## Support

For issues or questions, check the code comments or open an issue in the repository.
