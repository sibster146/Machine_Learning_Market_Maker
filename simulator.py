
import queue
import threading
import time
import math
from orderbook import OrderBook
from queue import Queue
from websocket import WebSocket, get_product_info
from model import BinaryClassifier
from portfolio import Portfolio
import os
import csv
from collections import deque
from avelleneda_stoikhov import AvellanedaStoikov

class AvellanedaStoikovMarketMaker:

    def __init__(self, symbol, binary_classifier, simulation_run, avellaneda_stoikov_parameters):
        self.updates_queue = Queue()
        self.websocket = WebSocket(self.updates_queue)
        self.symbol = symbol

        risk_aversion = avellaneda_stoikov_parameters["risk_aversion"]
        volatility = avellaneda_stoikov_parameters["volatility"]
        time_horizon = avellaneda_stoikov_parameters["time_horizon"]
        max_inventory_level = avellaneda_stoikov_parameters["max_inventory_level"]
        market_depth = avellaneda_stoikov_parameters["market_depth"]
        order_size = avellaneda_stoikov_parameters["order_size"]
        product_info = get_product_info(symbol)
        initial_mid_price = product_info["mid_price"]
        tick_size = product_info["tick_size"]


        self.as_algo = AvellanedaStoikov(
            gamma = risk_aversion,
            kappa = market_depth,
            sigma = volatility,
            T = time_horizon,
            q_max = max_inventory_level,
            mid_price=initial_mid_price,
            tick_size=tick_size
        )

        self.completed_trades_queue = Queue()
        self.ml_market_maker = MLMarketMaker(binary_classifier=binary_classifier, completed_trades_queue=self.completed_trades_queue, as_algo=self.as_algo, order_size=order_size)
        self.controlled_market_maker = ControlledMarketMaker(completed_trades_queue=self.completed_trades_queue, as_algo=self.as_algo, order_size=order_size)

        self.process_updates_queue_thread = threading.Thread(target=self.process_updates_queue)
        self.process_completed_trades_queue_thread = threading.Thread(target=self.process_completed_trades_queue)

        self.completed_trades_filename = f"simulations/{simulation_run}.csv"


    def start(self,):
        self.process_updates_queue_thread.start()
        self.process_completed_trades_queue_thread.start()
        self.websocket.open_socket(self.symbol)

    def stop(self):
        self.websocket.close_socket()
        self.updates_queue.put(None)
        self.completed_trades_queue.put(None)
        self.process_updates_queue_thread.join()
        self.process_completed_trades_queue_thread.join()

    def process_updates_queue(self):
        while 1:
            msg = self.updates_queue.get()
            if msg is None:
                return
            self.ml_market_maker.process_update(msg)
            self.controlled_market_maker.process_update(msg)
            self.updates_queue.task_done()

    def process_completed_trades_queue(self):
        while 1:
            msg = self.completed_trades_queue.get()
            if msg is None:
                return
            
            if not os.path.exists(self.completed_trades_filename):
                column_names = list(msg.keys())
                with open(self.completed_trades_filename, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(column_names)

            values = list(msg.values()) 
            with open(self.completed_trades_filename, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(values)
            
            self.completed_trades_queue.task_done()
            





class MLMarketMaker:
    def __init__(self, binary_classifier, completed_trades_queue, as_algo, order_size):
        self.completed_trades_queue = completed_trades_queue
        self.orderbook = OrderBook()
        self.portfolio = Portfolio()
        self.quoted_bid_price = None
        self.quoted_ask_price = None
        self.binary_classifier = binary_classifier
        self.up = 0
        self.positions = deque()
        self.as_algo = as_algo
        self.order_size = order_size



    def process_update(self,msg_json):
        if "updates" in msg_json["events"][0]:
            
            # Get curr bid and ask prices
            mm_curr_bid_price = self.quoted_bid_price
            mm_curr_ask_price = self.quoted_ask_price

            # Process updates for the orderbook
            updates = msg_json["events"][0]["updates"]
            self.orderbook.process_updates(updates)
            sequence_number = msg_json["sequence_num"]

            # Any marketable orders
            if mm_curr_ask_price and mm_curr_bid_price:
                curr_buy_volume = 0
                while self.orderbook.asks and curr_buy_volume < self.order_size and mm_curr_bid_price >= self.orderbook.asks[0][0]:
                    order_ask_price, order_ask_volume = self.orderbook.asks[0]
                    if curr_buy_volume + order_ask_volume > self.order_size:
                        needed_ask_volume = self.order_size - curr_buy_volume
                        curr_buy_volume += needed_ask_volume
                        self.orderbook.asks[0] = (order_ask_price, order_ask_volume - needed_ask_volume)
                    else:
                        curr_buy_volume += order_ask_volume
                        self.orderbook.asks.pop(0)

                if curr_buy_volume > 0:
                    self.portfolio.execute_order(mm_curr_bid_price, curr_buy_volume, is_buy=True)
                    if self.up:
                        self.portfolio.execute_order(mm_curr_bid_price, curr_buy_volume, is_buy=True)
                        self.positions.append((sequence_number + self.binary_classifier.update_lag-1, mm_curr_bid_price)) 

                    

                curr_sell_volume = 0
                while self.orderbook.bids and curr_sell_volume < self.portfolio.inventory and mm_curr_ask_price <= -self.orderbook.bids[0][0]:
                    order_bid_price, order_bid_volume = self.orderbook.bids[0]
                    if curr_sell_volume + order_bid_volume > self.portfolio.inventory:
                        needed_bid_volume = self.portfolio.inventory - curr_sell_volume
                        curr_sell_volume += needed_bid_volume
                        self.orderbook.bids[0] = (order_bid_price, order_bid_volume - needed_bid_volume)
                    else:
                        curr_sell_volume += order_bid_volume
                        self.orderbook.bids.pop(0)

                if curr_sell_volume > 0:
                    self.portfolio.execute_order(mm_curr_ask_price, curr_sell_volume, is_buy=False)
                    self.completed_trades_queue.put(
                        {
                        "model_type":1,
                        "sequence_number": sequence_number,
                        "pnl": self.portfolio.cash + self.portfolio.value - self.portfolio.initial_cash
                        }
                    )

            # Calculate mid price
            mid_price = self.orderbook.get_mid_price() # self.calculate_mid_price(product_id)
            if not mid_price:
                return
            
            # Update portfolio value
            self.portfolio.update(mid_price)

            bids, asks = self.orderbook.get_n_level_bids_asks(self.binary_classifier.price_level_num)
            timestamp_str = msg_json["timestamp"]
            self.up = self.binary_classifier.create_inference_vector(bids, asks, timestamp_str)

            bid_price, ask_price = self.as_algo.optimal_quotes(q = self.portfolio.inventory, t = sequence_number % 3)

            if not self.up:
                bid_price = -float("inf")
            if self.positions and self.positions[0][0] == sequence_number + 1:
                ask_price = max(ask_price,self.positions.popleft()[1] + 0.01)
                if bid_price > ask_price:
                    bid_price = ask_price

            self.quoted_ask_price = ask_price
            self.quoted_bid_price = bid_price


class ControlledMarketMaker:
    def __init__(self, completed_trades_queue, as_algo, order_size):
        self.completed_trades_queue = completed_trades_queue
        self.orderbook = OrderBook()
        self.portfolio = Portfolio()
        self.quoted_bid_price = None
        self.quoted_ask_price = None

        self.as_algo = as_algo
        self.order_size = order_size


    def process_update(self,msg_json):
        if "updates" in msg_json["events"][0]:
            

            # Get curr bid and ask prices
            mm_curr_bid_price = self.quoted_bid_price
            mm_curr_ask_price = self.quoted_ask_price
            sequence_number = msg_json["sequence_num"]

            # Process updates for the orderbook
            updates = msg_json["events"][0]["updates"]
            self.orderbook.process_updates(updates)

            # Any marketable orders
            if mm_curr_ask_price and mm_curr_bid_price:
                curr_buy_volume = 0
                while self.orderbook.asks and curr_buy_volume < self.order_size and mm_curr_bid_price >= self.orderbook.asks[0][0]:
                    order_ask_price, order_ask_volume = self.orderbook.asks[0]
                    if curr_buy_volume + order_ask_volume > self.order_size:
                        needed_ask_volume = self.order_size - curr_buy_volume
                        curr_buy_volume += needed_ask_volume
                        self.orderbook.asks[0] = (order_ask_price, order_ask_volume - needed_ask_volume)
                    else:
                        curr_buy_volume += order_ask_volume
                        self.orderbook.asks.pop(0)

                if curr_buy_volume > 0:
                    self.portfolio.execute_order(mm_curr_bid_price, curr_buy_volume, is_buy=True)

                curr_sell_volume = 0
                while self.orderbook.bids and curr_sell_volume < self.portfolio.inventory and mm_curr_ask_price <= -self.orderbook.bids[0][0]:
                    order_bid_price, order_bid_volume = self.orderbook.bids[0]
                    if curr_sell_volume + order_bid_volume > self.portfolio.inventory:
                        needed_bid_volume = self.portfolio.inventory - curr_sell_volume
                        curr_sell_volume += needed_bid_volume
                        self.orderbook.bids[0] = (order_bid_price, order_bid_volume - needed_bid_volume)
                    else:
                        curr_sell_volume += order_bid_volume
                        self.orderbook.bids.pop(0)

                if curr_sell_volume > 0:
                    self.portfolio.execute_order(mm_curr_ask_price, curr_sell_volume, is_buy=False)
                    self.completed_trades_queue.put(
                        {
                            "model_type":0,
                            "sequence_number": sequence_number,
                            "pnl": self.portfolio.cash + self.portfolio.value - self.portfolio.initial_cash
                        }
                    )

            # Calculate mid price
            mid_price = self.orderbook.get_mid_price() # self.calculate_mid_price(product_id)
            if not mid_price:
                return
            
            # Update portfolio value
            self.portfolio.update(mid_price)

            sequence_number = msg_json["sequence_num"]

            bid_price, ask_price = self.as_algo.optimal_quotes(q = self.portfolio.inventory, t = sequence_number % 3)

            self.quoted_ask_price = ask_price
            self.quoted_bid_price = bid_price
