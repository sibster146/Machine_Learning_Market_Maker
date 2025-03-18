from simulator import AvellanedaStoikovMarketMaker
from model import BinaryClassifier
import pickle
import joblib
import time
from pathlib import Path

if __name__ == '__main__':

    classifier_filename = "3_update_lag_xgbclassifier2.pkl"
    scaler_filename = "3_update_lag_xgbclassifier2_scaler.pkl"

    repo_path = Path("simulations")  # Change this to your repo's path
    file_count = sum(1 for _ in repo_path.rglob('*') if _.is_file())

    filename = "3_update_lag_xgbclassifier2.pkl"
    simulation_run = f"simulation_{file_count+1}_{filename}"

    print(f"Running {simulation_run}...")

    with open(classifier_filename, 'rb') as file:
        classifier_model = pickle.load(file)

    with open(scaler_filename, "rb") as file:
        scaler_model = joblib.load(file)

    price_level_num = 10
    historical_inference_max_length = 200
    update_lag = 3
    prob_limit = 0.8

    avellaneda_stoikov_parameters = {
        "risk_aversion": 0.01,
        "order_size": 0.001,
        "tick_size": 0.01,
        "volatility": 0.1,
        "time_horizon": 10,
        "max_inventory_level": 1,
        "market_depth": 2,
    }

    binary_classifier = BinaryClassifier(
        binary_classifier=classifier_model, price_level_num = price_level_num, 
        historical_inference_max_length= historical_inference_max_length, update_lag=update_lag, 
        filename=classifier_filename, prob_limit=prob_limit, scaler=scaler_model)
    
    market_maker = AvellanedaStoikovMarketMaker(
        symbol="BTC-USD",
        binary_classifier=binary_classifier, 
        simulation_run=simulation_run,
        avellaneda_stoikov_parameters = avellaneda_stoikov_parameters
        )

    market_maker.start()
    time.sleep(1800)
    market_maker.stop()




