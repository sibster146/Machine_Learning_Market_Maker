import numpy as np
import scipy.optimize as opt
from websocket import WebSocket

class AvellanedaStoikov:
    def __init__(self, gamma, kappa, sigma, T, q_max, mid_price, tick_size):
        """
        gamma: risk aversion parameter
        kappa: order book depth parameter
        sigma: volatility of the asset
        T: time horizon
        q_max: maximum inventory level
        mid_price: current mid price of the asset
        """
        self.gamma = gamma
        self.kappa = kappa
        self.sigma = sigma
        self.T = T
        self.q_max = q_max
        self.mid_price = mid_price
        self.tick_size = tick_size
    
    def optimal_quotes(self, q, t):
        """Calculate optimal bid and ask quotes based on current inventory q and time t"""
        tau = self.T - t  # Time to maturity
        if tau <= 0:
            return self.mid_price, self.mid_price
        
        # Compute reservation price
        reservation_price = self.mid_price - q * self.gamma * (self.sigma ** 2) * tau
        
        # Compute spread
        spread = (self.gamma * (self.sigma ** 2) * tau) + (2 / self.gamma) * np.log(1 + (self.gamma / self.kappa))
        
        # Compute bid and ask prices
        bid_price = round((reservation_price - spread / 2) / self.tick_size) * self.tick_size
        ask_price = round((reservation_price + spread / 2) / self.tick_size) * self.tick_size

        print(bid_price, ask_price)


        
        return bid_price, ask_price