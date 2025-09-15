# EC2 Testnet Miner Setup with PM2 - Todo List

## COMPLETED SETUP SUMMARY ✅
- **Instance Created**: `i-0f7a60b94ba21a51d` (30GB disk, t3.small)
- **Public IP**: `3.21.247.112`
- **Key Pair**: `testnet-miner-4-key` (saved to `~/.ssh/testnet-miner-4-key.pem`)
- **Security Group**: `sg-02632a1cd3f9c7ff2` (SSH access configured)
- **Wallet Created**: `testnet_miner_4` with 5 TAO transferred
- **Coldkey Address**: `5ELVuwZFBaYtfX845ewWrxP6sQubMCSPozerYFcnm9Etk7Pi`
- **Hotkey Address**: `5EjVGhVu5y4iFCZxVxsGAF7sVD77MuMKuTPLJitDE1AbV2yK`

## WALLET RECOVERY INFO (SECURE THESE!)
- **Coldkey Mnemonic**: `assault uncover abuse enjoy bread dust meadow scatter relax dinosaur assault concert`
- **Hotkey Mnemonic**: `pudding fruit engine dove shoot title team ivory pole gentle crime satoshi`

## Phase 1: EC2 Instance Creation & Setup ✅

### 1.1 Create EC2 Instance ✅
- [x] Launch new EC2 instance using AWS CLI with resilabs-admin profile
  ```bash
  # EXECUTED: Created i-0f7a60b94ba21a51d with 30GB disk
  aws ec2 run-instances \
    --image-id ami-0403a1833008b227d \
    --instance-type t3.small \
    --key-name testnet-miner-4-key \
    --security-group-ids sg-02632a1cd3f9c7ff2 \
    --subnet-id subnet-0c3412270b089f592 \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=testnet-miner-4}]' \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":30,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
    --profile resilabs-admin
  ```

### 1.2 Configure Security Group ✅
- [x] Create/update security group to allow:
  - SSH (port 22) from your IP (162.84.164.68/32)
  - Bittensor ports (9944, 30333) if needed
  - Any custom monitoring ports

### 1.3 Connect to Instance
- [x] Get instance public IP from AWS console or CLI: `3.21.247.112`
- [ ] SSH into instance: `ssh -i ~/.ssh/testnet-miner-4-key.pem ubuntu@3.21.247.112`
- [ ] Update system: `sudo apt update && sudo apt upgrade -y`

## Phase 2: System Dependencies Installation

### 2.1 Install Python & Git
- [ ] Install Python 3.11+: `sudo apt install python3.11 python3.11-venv python3-pip git -y`
- [ ] Verify Python version: `python3 --version`
- [ ] Install build essentials: `sudo apt install build-essential -y`

### 2.2 Install Node.js & PM2
- [ ] Install Node.js: `curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -`
- [ ] Install Node.js: `sudo apt-get install -y nodejs`
- [ ] Install PM2 globally: `sudo npm install -g pm2`
- [ ] Verify PM2 installation: `pm2 --version`

## Phase 3: Bittensor Wallet Setup

### 3.1 Create New Wallet & Hotkey
- [ ] Install bittensor: `pip3 install bittensor`
- [ ] Create new wallet: `btcli wallet new_coldkey --wallet.name testnet_miner_4`
- [ ] Create new hotkey: `btcli wallet new_hotkey --wallet.name testnet_miner_4 --wallet.hotkey hotkey_4`
- [ ] Check wallet balance: `btcli wallet balance --wallet.name testnet_miner_4 --subtensor.network test`

### 3.2 Fund Wallet (if needed)
- [ ] Get testnet TAO from faucet if balance is low
- [ ] Verify sufficient balance for registration (>1 TAO recommended)

## Phase 4: Miner Registration

### 4.1 Register as Miner
- [ ] Register on subnet 428:
  ```bash
  btcli subnet register \
    --netuid 428 \
    --subtensor.network test \
    --wallet.name testnet_miner_4 \
    --wallet.hotkey hotkey_4
  ```
- [ ] Verify registration: `btcli subnet list --subtensor.network test`
- [ ] Check miner UID: `btcli wallet overview --wallet.name testnet_miner_4 --subtensor.network test`

## Phase 5: Code Deployment

### 5.1 Clone Repository
- [ ] Clone repo: `git clone https://github.com/ResiLabs/resi.git`
- [ ] Navigate to directory: `cd resi`
- [ ] Check current branch: `git branch`

### 5.2 Environment Setup
- [ ] Create Python virtual environment: `python3 -m venv venv`
- [ ] Activate venv: `source venv/bin/activate`
- [ ] Install dependencies: `pip install -r requirements.txt`

### 5.3 Environment Configuration
- [ ] Copy environment template: `cp env.example .env`
- [ ] Edit .env file with miner-specific values:
  ```bash
  nano .env
  ```
  Update:
  - WALLET_NAME=testnet_miner_4
  - WALLET_HOTKEY=hotkey_4
  - RAPIDAPI_KEY=b869b7feb4msh25a74b696857db1p19cfd0jsnbc9d2e2e820f
  - RAPIDAPI_HOST=zillow-com1.p.rapidapi.com
  - NETUID=428
  - SUBTENSOR_NETWORK=test

## Phase 6: PM2 Configuration & Startup

### 6.1 Create PM2 Ecosystem File
- [ ] Create PM2 config file: `nano ecosystem.config.js`
  ```javascript
  module.exports = {
    apps: [{
      name: 'testnet-miner-4',
      script: 'python',
      args: 'neurons/miner.py --netuid 428 --subtensor.network test --wallet.name testnet_miner_4 --wallet.hotkey hotkey_4 --use_uploader --logging.debug --neuron.database_name SqliteMinerStorage_miner4.sqlite --miner_upload_state_file upload_utils/state_file_miner4.json',
      cwd: '/home/ubuntu/resi',
      interpreter: '/home/ubuntu/resi/venv/bin/python',
      env: {
        NODE_ENV: 'production'
      },
      error_file: './logs/miner4-error.log',
      out_file: './logs/miner4-out.log',
      log_file: './logs/miner4-combined.log',
      time: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s'
    }]
  };
  ```

### 6.2 Create Log Directory & State Files
- [ ] Create logs directory: `mkdir -p logs`
- [ ] Create upload utils state file: `touch upload_utils/state_file_miner4.json`
- [ ] Initialize state file: `echo '{}' > upload_utils/state_file_miner4.json`

### 6.3 Start Miner with PM2
- [ ] Start miner: `pm2 start ecosystem.config.js`
- [ ] Check status: `pm2 status`
- [ ] View logs: `pm2 logs testnet-miner-4`
- [ ] Save PM2 configuration: `pm2 save`
- [ ] Setup PM2 startup: `pm2 startup` (follow the generated command)

## Phase 7: Monitoring & Verification

### 7.1 Verify Miner Operation
- [ ] Check PM2 status: `pm2 monit`
- [ ] Check logs for errors: `pm2 logs testnet-miner-4 --lines 50`
- [ ] Verify database creation: `ls -la SqliteMinerStorage_miner4.sqlite`
- [ ] Check network connectivity to bittensor

### 7.2 Monitor Registration Status
- [ ] Check miner is visible on network:
  ```bash
  btcli subnet metagraph --netuid 428 --subtensor.network test
  ```
- [ ] Verify miner UID and stake information

## Phase 8: Cleanup & Documentation

### 8.1 Security Hardening
- [ ] Remove unnecessary packages: `sudo apt autoremove -y`
- [ ] Update firewall rules if needed
- [ ] Secure wallet files with proper permissions: `chmod 600 ~/.bittensor/wallets/testnet_miner_4/*`

### 8.2 Create Backup & Recovery Notes
- [ ] Document wallet recovery phrase (store securely offline)
- [ ] Note down instance details (IP, instance ID, key pair)
- [ ] Document PM2 management commands for future reference

## Useful Commands for Management

### PM2 Management
```bash
pm2 status                    # Check all processes
pm2 logs testnet-miner-4     # View logs
pm2 restart testnet-miner-4  # Restart miner
pm2 stop testnet-miner-4     # Stop miner
pm2 delete testnet-miner-4   # Remove from PM2
pm2 monit                    # Real-time monitoring
```

### Bittensor Commands
```bash
btcli wallet balance --wallet.name testnet_miner_4 --subtensor.network test
btcli subnet metagraph --netuid 428 --subtensor.network test
btcli wallet overview --wallet.name testnet_miner_4 --subtensor.network test
```

### System Monitoring
```bash
htop                         # System resources
df -h                        # Disk usage
free -h                      # Memory usage
pm2 logs testnet-miner-4     # Application logs
```

## Notes
- Instance type t3.small should be sufficient for testnet mining
- Monitor costs and upgrade if performance is insufficient
- Keep wallet backup secure and offline
- Regularly check miner performance and logs
- Consider setting up CloudWatch monitoring for production use
