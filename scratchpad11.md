btcli sudo set hyperparameters \
    --netuid 46 \
    --param weights_rate_limit \
    --value 360 \
    --subtensor.network finney \
    --wallet.name sn46cold

btcli sudo set hyperparameters \
    --netuid 46 \
    --param adjustment_alpha \
    --value 17893341751498264576 \
    --subtensor.network finney \
    --wallet.name sn46cold

btcli sudo set hyperparameters \
    --netuid 46 \
    --param immunity_period \
    --value 12000 \
    --subtensor.network finney \
    --wallet.name sn46cold