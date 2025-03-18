import bisect
import numpy as np
class OrderBook:
    def __init__(self):
        self.asks = []
        self.bids = []            

    def get_n_level_bids_asks(self, n):

        asks = np.array(self.asks[:n])
        bids = np.array(self.bids[:n])
        bids[:,0] = -bids[:,0]

        return bids,asks
    
    def get_x_percentage_level_bids_asks(self,x):
        mid_price = self.get_mid_price()
        top_x_price = mid_price + (mid_price*x)
        bottom_x_price = mid_price - (mid_price*x)

        asks = []
        bids = []

        i = 0
        while i < len(self.asks) and self.asks[i][0] <= top_x_price:
            asks.append(self.asks[i])
            i+=1
        i = 0
        while i < len(self.bids) and -self.bids[i][0] >= bottom_x_price:
            bids.append(self.bids[i])
            i+=1

        asks = np.array(asks)
        bids = np.array(bids)
        bids[:,0] = -bids[:,0]

        return bids,asks

        

        



    def get_mid_price(self):
        if len(self.asks) == 0 and len(self.bids) == 0:
            return None
        return (self.asks[0][0] + (-self.bids[0][0])) / 2


    def process_updates(self, updates):
        for update in updates:
            self.update_level(update)


    def find_price_level_binary(self, data, target):
        l = 0
        r = len(data)-1

        while l <= r:
            m = (l+r)//2
            if data[m][0] == target:
                return m
            if data[m][0] > target:
                r = m-1
            else:
                l = m+1
        return -1


    def update_level(self, update):
        side = update["side"]
        new_price = float(update["price_level"])
        new_quantity = float(update["new_quantity"])
        if side == "offer":
            price_level_index = self.find_price_level_binary(self.asks, new_price)
            if new_quantity > 0.0:
                if price_level_index >= 0:
                    self.asks[price_level_index] = (new_price, new_quantity)
                else:
                    bisect.insort(self.asks, (new_price, new_quantity))
            else:
                if price_level_index >= 0:
                    self.asks.pop(price_level_index)
        else:
            new_price = new_price * -1
            price_level_index = self.find_price_level_binary(self.bids, new_price)
            if new_quantity > 0.0:
                if price_level_index >= 0:
                    self.bids[price_level_index] = (new_price,new_quantity)
                else:
                    bisect.insort(self.bids, (new_price, new_quantity))
            else:
                if price_level_index >= 0:
                    self.bids.pop(price_level_index)


    




