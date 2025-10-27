# PM2 Process Management Guide

This guide covers PM2 installation, configuration, and process management for reliable application deployment.

## Installation

### Install Node.js and PM2
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo npm install -g pm2
```

### Verify Installation
```bash
node --version
pm2 --version
```

## Process Management

### Starting Processes

#### Miner Process
```bash
# Start miner on testnet
pm2 start python --name testnet-miner -- ./neurons/miner.py \
  --netuid 428 \
  --subtensor.network test \
  --wallet.name your_wallet \
  --wallet.hotkey your_hotkey \
  --use_uploader \
  --logging.debug

# Start miner on mainnet
pm2 start python --name mainnet-miner -- ./neurons/miner.py \
  --netuid 46 \
  --subtensor.network finney \
  --wallet.name your_wallet \
  --wallet.hotkey your_hotkey \
  --use_uploader \
  --logging.debug
```

#### Validator Process
```bash
# Start validator on testnet
pm2 start python --name testnet-validator -- ./neurons/validator.py \
  --netuid 428 \
  --subtensor.network test \
  --wallet.name your_wallet \
  --wallet.hotkey your_hotkey \
  --max_targets 10 \
  --logging.debug

# Start validator on mainnet
pm2 start python --name mainnet-validator -- ./neurons/validator.py \
  --netuid 46 \
  --subtensor.network finney \
  --wallet.name your_wallet \
  --wallet.hotkey your_hotkey \
  --max_targets 10 \
  --logging.debug
```


### Process Control
```bash
# List all processes
pm2 list

# Show process details
pm2 show <process-name>

# Restart a process
pm2 restart <process-name>

# Stop a process
pm2 stop <process-name>

# Delete a process
pm2 delete <process-name>
```

### Monitoring and Logs
```bash
# View logs for all processes
pm2 logs

# View logs for specific process
pm2 logs <process-name>

# View last N lines
pm2 logs <process-name> --lines 200

# Follow logs in real-time
pm2 logs <process-name> --follow

# Monitor process status
pm2 monit
```

## Startup Configuration

### Auto-start on Boot
```bash
# Save current process list
pm2 save

# Generate and enable startup script
pm2 startup

# Follow the instructions printed by PM2 to complete setup
```

## Environment Configuration

### Environment Variables for RESI Processes

Create a `.env` file for your RESI environment variables:
```env
NETUID=46
SUBTENSOR_NETWORK=finney
WALLET_NAME=your_wallet
WALLET_HOTKEY=your_hotkey
```

For proxy configuration, add:
```env
HTTP_PROXY=http://username:password@proxy-server:port
HTTPS_PROXY=http://username:password@proxy-server:port
SCRAPINGBEE_API_KEY=your_api_key_here
```

### Process Recovery
```bash
# Resurrect processes after reboot
pm2 resurrect

# List failed processes
pm2 jlist

# Clear process list
pm2 kill
```