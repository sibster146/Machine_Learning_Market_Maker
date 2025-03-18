import pickle
import numpy as np
import pandas as pd

class BinaryClassifier:
    def __init__(self, binary_classifier, price_level_num, historical_inference_max_length, update_lag, filename, prob_limit, scaler = None):
        self.price_level_num = price_level_num
        self.historical_inference_vectors = pd.DataFrame()
        self.binary_classifier = binary_classifier
        self.historical_inference_max_length = historical_inference_max_length
        self.update_lag = update_lag
        self.name = filename
        self.probability_limit = prob_limit
        self.scaler = scaler


    def create_inference_vector(self, bids, asks, timestamp_str):

        inf_row = {}

        for i in range(self.price_level_num):
            inf_row[f"Bid Price Level {i+1}"] = bids[i][0]
            inf_row[f"Bid Volume Level {i+1}"] = bids[i][1]
            inf_row[f"Ask Price Level {i+1}"] = asks[i][0]
            inf_row[f"Ask Volume Level {i+1}"] = asks[i][1]

        inf_row["Timestamp"] = timestamp_str

        inf_df = pd.DataFrame([inf_row])

        inf_df = self.time_independent_features(inf_df, self.price_level_num)

        inf_df = self.time_dependent_features(inf_df, [1,2,5,10])

        feature_columns = [
            # 'Mid Price', 
            
            'Bid Ask Spread',
            
            'Bid Volume Level 1','Bid Volume Level 2','Bid Volume Level 3',
            # 'Bid Volume Level 4',
            # 'Bid Volume Level 5','Bid Volume Level 6','Bid Volume Level 7', 'Bid Volume Level 8',
            # 'Bid Volume Level 9','Bid Volume Level 10',
            
            'Ask Volume Level 1','Ask Volume Level 2','Ask Volume Level 3', 
            # 'Ask Volume Level 4',
            # 'Ask Volume Level 5','Ask Volume Level 6','Ask Volume Level 7', 'Ask Volume Level 8',
            # 'Ask Volume Level 9','Ask Volume Level 10',

            # 'Bid Price Level 1','Bid Price Level 2','Bid Price Level 3', 
            # 'Bid Price Level 4',
            # 'Bid Price Level 5','Bid Price Level 6','Bid Price Level 7', 'Bid Price Level 8',
            # 'Bid Price Level 9','Bid Price Level 10',
            
            # 'Ask Price Level 1','Ask Price Level 2','Ask Price Level 3', 
            # 'Ask Price Level 4',
            # 'Ask Price Level 5','Ask Price Level 6','Ask Price Level 7', 'Ask Price Level 8',
            # 'Ask Price Level 9','Ask Price Level 10',
            
            'Bid Volume Level 1 Log','Bid Volume Level 2 Log','Bid Volume Level 3 Log', 'Bid Volume Level 4 Log',
            'Bid Volume Level 5 Log',
            # 'Bid Volume Level 6 Log','Bid Volume Level 7 Log', 'Bid Volume Level 8 Log',
            # 'Bid Volume Level 9 Log','Bid Volume Level 10 Log',
            
            'Ask Volume Level 1 Log','Ask Volume Level 2 Log','Ask Volume Level 3 Log', 'Ask Volume Level 4 Log',
            'Ask Volume Level 5 Log',
            # 'Ask Volume Level 6 Log','Ask Volume Level 7 Log', 'Ask Volume Level 8 Log',
            # 'Ask Volume Level 9 Log','Ask Volume Level 10 Log',
            
            # 'Bid Volume Diff 1', 'Bid Volume Diff 2', 'Bid Volume Diff 3',
            # 'Bid Volume Diff 4', 'Bid Volume Diff 5', 'Bid Volume Diff 6',
            # 'Bid Volume Diff 7', 'Bid Volume Diff 8', 'Bid Volume Diff 9',
            
            # 'Ask Volume Diff 1', 'Ask Volume Diff 2', 'Ask Volume Diff 3',
            # 'Ask Volume Diff 4', 'Ask Volume Diff 5', 'Ask Volume Diff 6',
            # 'Ask Volume Diff 7', 'Ask Volume Diff 8', 'Ask Volume Diff 9',
            
            'Imbalance',
            'Mid Price Velocity',
            'Mid Price Acceleration',
            'Time Since Last Update',
            'Bid VWAP 10',
            'Ask VWAP 10', 
            # 'Total Bid Volume 10',
            # 'Total Ask Volume 10', 
            'Price Range', 
            "Mid Price Volatility 2","Mid Price Volatility 5","Mid Price Volatility 10",
                #'Mid Price SMA 1', 'Mid Price SMA 2', 'Mid Price SMA 5','Mid Price SMA 10',
            #'Mid Price ROC',
            #'Mid Price EMA 1', 'Mid Price EMA 2', 'Mid Price EMA 5', 'Mid Price EMA 10',
            'Mid Price RSI'
        ] 

        self.historical_inference_vectors = pd.concat([self.historical_inference_vectors,inf_df], ignore_index= True)
        if len(self.historical_inference_vectors) > 400:
            self.historical_inference_vectors = self.historical_inference_vectors.tail(200)

        X = inf_df[feature_columns]

        if X.isna().any().any():
            return False
        

        if self.scaler:
            X = self.scaler.transform(X)
            
        prob  = self.binary_classifier.predict_proba(X)[0][1]

        return prob >= self.probability_limit




    def time_independent_features(self,df, price_level_num):

        # Mid Price
        df["Mid Price"] = (df["Bid Price Level 1"] + df["Ask Price Level 1"]) / 2

        # Mid Price Velocity
        if len(self.historical_inference_vectors) < 1:
            df["Mid Price Velocity"] = np.nan
        else:
            df["Mid Price Velocity"] = df["Mid Price"] - self.historical_inference_vectors.iloc[-1]["Mid Price"]

        # Mid Price Acceleration
        if len(self.historical_inference_vectors) < 2:
            df["Mid Price Acceleration"] = np.nan
        else:
            df["Mid Price Acceleration"] = df["Mid Price Velocity"] - self.historical_inference_vectors.iloc[-1]["Mid Price Velocity"]
        
        # Bid Ask Spread
        df["Bid Ask Spread"] = (df["Bid Price Level 1"] - df["Ask Price Level 1"])
        
        # Volume Level Log Bid & Ask
        for i in range(price_level_num):
            df[f"Bid Volume Level {i+1} Log"] = np.log(df[f"Bid Volume Level {i+1}"])
        for i in range(price_level_num):
            df[f"Ask Volume Level {i+1} Log"] = np.log(df[f"Ask Volume Level {i+1}"])
        
        # Volume Level Difference Bid & Ask
        for i in range(1,price_level_num):
            df[f'Bid Volume Diff {i}'] = df[f'Bid Volume Level {i+1}'] - df[f'Bid Volume Level {i}']
        for i in range(1,price_level_num):
            df[f'Ask Volume Diff {i}'] = df[f'Ask Volume Level {i+1}'] - df[f'Ask Volume Level {i}']
        
        # Imbalance
        df["Imbalance"] = (df["Bid Volume Level 1"] - df["Ask Volume Level 1"]) / (df["Bid Volume Level 1"] + df["Ask Volume Level 1"])
        
        # VWAP Bid & Ask
        def vwap_helper(df, side, levels):
            total_volume = sum(df[[f"{side} Volume Level {i}" for i in range(1,levels+1)]].values)
            vwap = sum(df[f'{side} Price Level {i}'] * df[f'{side} Volume Level {i}'] for i in range(1, levels+1)) / total_volume
            return vwap
        df[f"Bid VWAP {price_level_num}"] = df.apply(lambda row: vwap_helper(row, "Bid", price_level_num), axis = 1)
        df[f"Ask VWAP {price_level_num}"] = df.apply(lambda row: vwap_helper(row, "Ask", price_level_num), axis = 1)
       
        # Total Volume Bid & Ask
        df[f"Total Bid Volume {price_level_num}"] = df[[f'Bid Volume Level {i}' for i in range(1, price_level_num+1)]].sum(axis=1)
        df[f"Total Ask Volume {price_level_num}"] = df[[f'Ask Volume Level {i}' for i in range(1, price_level_num+1)]].sum(axis=1)
        
        # Price Range
        df["Price Range"] = df[f"Ask Price Level {self.price_level_num}"] - df[f"Bid Price Level {self.price_level_num}"]
        
        # Time Difference
        df['Timestamp'] = pd.to_datetime(df['Timestamp'],format='ISO8601')
        if len(self.historical_inference_vectors) >= 1:
            df['Time Since Last Update'] = (df['Timestamp'] - self.historical_inference_vectors.iloc[-1]["Timestamp"]).dt.total_seconds()
        else:
            df['Time Since Last Update'] = np.nan

        return df

    def time_dependent_features(self, df, windows):

        temp_df = pd.concat([self.historical_inference_vectors, df], ignore_index = True)

        mid_prices_series = temp_df["Mid Price"]
                
        # Mid Price Volatility Calculation
        def volatility_helper(series, window):
            if len(series) >= window:
                std = series.tail(window).std()
                return std
            return np.nan
        
        for window in windows:
            if window == 1:
                continue
            df[f"Mid Price Volatility {window}"] = volatility_helper(mid_prices_series, window)

        

        def create_sma_helper(series, window):

            if len(series) < window:
                return np.nan

            return sum(series.tail(window)) / window
        
        for window in windows:
            df[f"Mid Price SMA {window}"] = create_sma_helper(mid_prices_series, window)


        
        def create_rate_of_change_helper(series):
            if len(series) < 2:
                return np.nan

            return (series.iloc[-1] - series.iloc[-2]) / (series.iloc[-2])
        
        df[f"Mid Price ROC"] = create_rate_of_change_helper(mid_prices_series)


        
        def create_ema_helper(series, window):
            alpha = 2 / (window+1)
            ema = [None]*len(series)
            if len(self.historical_inference_vectors) == 0:
                ema[0] = df["Mid Price"]
            else:
                ema[0] = self.historical_inference_vectors.iloc[-1][f"Mid Price EMA {window}"]

            for i in range(1, len(series)):
                ema[i] = (alpha * series[i] + (1-alpha) * ema[i-1])
            return ema[-1]
        
        for window in windows:
            df[f"Mid Price EMA {window}"] = create_ema_helper(mid_prices_series, window)


        
        def create_rsi_helper(series, window):
            deltas = [None]*len(series)
            for i in range(1,len(series)):
                deltas[i] = series[i] - series[i-1]
        
            gains = [max(delta, 0) if delta is not None else None for delta in deltas]
            losses = [-min(delta, 0) if delta is not None else None for delta in deltas]
        
            avg_gain = create_sma_helper(pd.Series(gains),window)
            avg_loss = create_sma_helper(pd.Series(losses),window)

            if avg_loss == None or avg_gain == None:
                return None

            if avg_loss == 0:
                return 100

            rs = avg_gain / avg_loss
                
            rsi =  (100 - (100 / (1 + rs)))
            
            return rsi
        

        df["Mid Price RSI"] = create_rsi_helper(mid_prices_series, window=14)

        return df




    
