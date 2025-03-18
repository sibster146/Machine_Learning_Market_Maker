class Portfolio:
    def __init__(self):
        self.cash = 100000  # Starting cash in USDT
        self.initial_cash = self.cash
        self.inventory = 0
        self.value = 0

    def update(self, price):
        self.value = self.inventory * price

    def execute_order(self, price, size, is_buy):
        if size == 0:
            return

        value = price * size
        if is_buy:
            self.cash -= value
            self.inventory += size
        else:
            self.cash += value
            self.inventory -= size

        self.value = self.inventory * price

    def calculate_pnl(self):

        realized_pnl = self.cash - self.initial_cash

        # for _,position_value in self.holding.values():
        #     unrealized_pnl += position_value
        
        total_pnl = realized_pnl + self.value

        return self.value, realized_pnl, total_pnl