import numpy as np
from collections import deque
class AvellanedaStoikov:
    def __init__(self, time_horizon, volatility_window, price_level_num):
        self.time_horizon = time_horizon
        self.mid_prices = deque()
        self.price_level_num = price_level_num
        self.volatility_window = volatility_window

    def get_reservation_price(self, mid_price, target_inventory, risk_aversion, volatility, time_until_end):
        return mid_price - target_inventory*risk_aversion*(volatility**2)*time_until_end

    def get_spread(self, risk_aversion, volatility, time_until_end, liquidity_density):
        return risk_aversion*(volatility**2)*time_until_end + ((2/risk_aversion) * (np.log(1 + (risk_aversion / liquidity_density))))
    

    def get_bid_ask_prices(self, mid_price, bids, asks, sequence_number, ml = 1e-9):

        self.mid_prices.append(mid_price)
        if len(self.mid_prices) < self.volatility_window:
            return None
        while len(self.mid_prices) > self.volatility_window:
            self.mid_prices.popleft()

        # Reservation Price and Spread
        # risk_aversion_base = 0.05
        # alpha_imbalance = 0.01
        bids_volume = sum(bids[:,1])
        asks_volume = sum(asks[:,1])
        bids_volume = sum(bids[:,1])
        asks_volume = sum(asks[:,1])
        # imbalance = (bids_volume - asks_volume) / (bids_volume + asks_volume)
        risk_aversion = ml# risk_aversion_base * (1 + alpha_imbalance * abs(imbalance))
        time_until_end = (self.time_horizon - (sequence_number + 1)) / self.time_horizon
        volatility = np.std(self.mid_prices)
        # target_inventory = 1
        reservation_price = self.get_reservation_price(mid_price=mid_price, target_inventory=ml, risk_aversion=risk_aversion, volatility=volatility, time_until_end=time_until_end)
        base_density = 0.5
        liquidity_density = 1 # max(0.2, min(0.8, base_density + imbalance * 0.2))
        spread = self.get_spread(risk_aversion=risk_aversion, volatility=volatility, time_until_end=time_until_end, liquidity_density=liquidity_density)

        bid_price = reservation_price - (spread / 2)
        ask_price = reservation_price + (spread / 2)
        return bid_price, ask_price
