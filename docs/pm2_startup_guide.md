# PM2 Startup Guide

This guide helps you configure PM2 to manage miner and validator processes reliably.

## Common Steps

1. Install Node.js and PM2
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo npm install -g pm2
```

2. Verify installations
```bash
node --version
pm2 --version
```

## Miner Process

Example PM2 command to run a miner on testnet:
```bash
pm2 start python --name testnet-miner -- ./neurons/miner.py \
  --netuid 428 \
  --subtensor.network test \
  --wallet.name your_wallet \
  --wallet.hotkey your_hotkey \
  --use_uploader \
  --logging.debug
```

## Validator Process

Example PM2 command to run a validator on testnet:
```bash
pm2 start python --name testnet-validator -- ./neurons/validator.py \
  --netuid 428 \
  --subtensor.network test \
  --wallet.name your_wallet \
  --wallet.hotkey your_hotkey \
  --max_targets 10 \
  --logging.debug
```

## PM2 Startup on Boot

```bash
pm2 save
pm2 startup
# Follow the instructions printed by PM2 to enable the startup script
```

## Environment Variables

Create a `.env` file for your environment and set wallet details and network:
```env
NETUID=428
SUBTENSOR_NETWORK=test
WALLET_NAME=your_wallet
WALLET_HOTKEY=your_hotkey
```

If you use proxies for validation scraping, add the relevant variables:
```env
# PROXY_HOST=...
# PROXY_PORT=...
# PROXY_USER=...
# PROXY_PASS=...
```

## Troubleshooting

- Ensure your virtual environment is activated before starting PM2 processes
- Check logs with `pm2 logs <process-name> --lines 200 --follow`
- Restart a process with `pm2 restart <process-name>`
- Validate wallet registration: `btcli wallet overview --subtensor.network test --wallet.name your_wallet`
