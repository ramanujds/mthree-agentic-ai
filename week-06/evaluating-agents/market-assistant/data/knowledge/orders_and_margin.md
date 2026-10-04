# Orders and Margin

## Order types
A market order is executed immediately at the best available price. A limit order is executed only at the limit price or better. A stop-loss order becomes a market or limit order once the trigger price is reached. This assistant supports only market orders for delivery.

## Delivery and intraday
A delivery order holds the shares overnight and they are credited to the demat account. An intraday order must be squared off on the same day. This assistant supports delivery orders only.

## Quantity
Shares are bought and sold in whole units. The minimum order quantity is 1 share. Fractional shares are not available.

## Funds and holdings required
A buy order needs enough available cash to cover the trade value plus all charges. Margin or leverage is not offered by this assistant, so every buy is paid fully in cash. A sell order needs enough shares in the demat account. Short selling is not allowed for delivery orders, so a client cannot sell more shares than they hold.

## Order rejection
An order is rejected if the market is closed, if the symbol is not found, if cash is insufficient for a buy, or if holdings are insufficient for a sell. A rejected order has no effect on cash or holdings.
