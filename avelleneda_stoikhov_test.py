import numpy as np
import scipy.optimize as opt
from websocket import WebSocket
from queue import Queue
from orderbook import OrderBook
from collections import deque
import threading
from time import sleep
class AvellanedaStoikov:
    def __init__(self, time_horizon ):
        self.queue = Queue()
        self.websocket = WebSocket(self.queue)
        self.orderbook = OrderBook()
        self.mid_prices = deque()
        self.time_horizon = time_horizon
        self.process_queue_thread = threading.Thread(target = self.process_queue)

    def run(self):
        print("running")
        self.process_queue_thread.start()
        self.websocket.open_socket("BTC-USD")



    def process_queue(self):
        while 1:
            msg = self.queue.get()
            if msg is None:
                return
            
            self.process_msg(msg)
            self.queue.task_done()

    def get_reservation_price(self, mid_price, target_inventory, risk_aversion, volatility, time_until_end):
        return mid_price - target_inventory*risk_aversion*(volatility**2)*time_until_end
    
    def get_spread(self, risk_aversion, volatility, time_until_end, liquidity_density):
        return risk_aversion*(volatility**2)*time_until_end + ((2/risk_aversion) * (np.log(1 + (risk_aversion / liquidity_density))))
    
    

            

    def process_msg(self, msg_json):
        if "updates" in msg_json["events"][0]:
            
            sequence_number = msg_json["sequence_num"]

            # Process updates for the orderbook
            updates = msg_json["events"][0]["updates"]
            self.orderbook.process_updates(updates)

            # Calculate mid price
            mid_price = self.orderbook.get_mid_price() # self.calculate_mid_price(product_id)
            if not mid_price:
                return
            self.mid_prices.append(mid_price)
            if len(self.mid_prices) < 10:
                return
            while len(self.mid_prices) > 25:
                self.mid_prices.popleft()

            # Reservation Price and Spread
            risk_aversion_base = 0.05
            alpha_imbalance = 0.01
            #bids, asks = self.orderbook.get_x_percentage_level_bids_asks(1)
            bids, asks = self.orderbook.get_n_level_bids_asks(10)
            bids_volume = sum(bids[:,1])
            asks_volume = sum(asks[:,1])
            imbalance = (bids_volume - asks_volume) / (bids_volume + asks_volume)
            risk_aversion = risk_aversion_base * (1 + alpha_imbalance * abs(imbalance))
            time_until_end = (self.time_horizon - (sequence_number + 1)) / self.time_horizon
            volatility = np.std(self.mid_prices)
            reservation_price = self.get_reservation_price(mid_price=mid_price, target_inventory=0, risk_aversion=risk_aversion, volatility=volatility, time_until_end=time_until_end)
            base_density = 0.5
            liquidity_density = max(0.2, min(0.8, base_density + imbalance * 0.2))
            spread = self.get_spread(risk_aversion=risk_aversion, volatility=volatility, time_until_end=time_until_end, liquidity_density=liquidity_density)

            bid_price = reservation_price - (spread / 2)
            ask_price = reservation_price + (spread / 2)

            print(bid_price, ask_price, -self.orderbook.bids[0][0], self.orderbook.asks[0][0], imbalance)


m = AvellanedaStoikov(time_horizon=3)

m.run()

            

