import ccxt
import datetime
import pandas as pd
import time
import numpy as np
from typing import Dict, List, Optional, Any
import os
import logging
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split # Although the article uses time-based split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib # For saving/loading the model

# Configure logging (assuming you have a logging_config module, otherwise use basicConfig)
# import logging_config
# logging_config.setup_logging()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
EXCHANGE_ID = 'okx'
SYMBOL_SPOT = 'BTC/USDT' # Spot symbol
SYMBOL_SWAP = 'BTC/USDT:USDT' # Perpetual swap symbol for OKX
LOOKBACK_DAYS_TRAIN = 30 # Days of data for training (as per article)
LOOKBACK_DAYS_TEST = 7 # Days of data for testing (as per article)
MODEL_FILE = 'funding_rate_model.pkl' # File to save the trained model

# TODO: Load API keys securely if needed for fetching historical data (usually not required for public data)
# OKX_API_KEY = os.getenv('OKX_API_KEY')
# OKX_SECRET_KEY = os.getenv('OKX_SECRET_KEY')
# OKX_PASSPHRASE = os.getenv('OKX_PASSPHRASE')
# OKX_SANDBOX = os.getenv('OKX_SANDBOX', 'false').lower() == 'true'

# --- Data Collection ---

def fetch_historical_data(exchange_id: str, symbol_spot: str, symbol_swap: str, lookback_days: int) -> Optional[pd.DataFrame]:
    """
    Fetches historical spot prices, swap prices, and funding rates.

    Args:
        exchange_id: Exchange ID.
        symbol_spot: Spot symbol.
        symbol_swap: Perpetual swap symbol.
        lookback_days: Number of days to fetch data for.

    Returns:
        Pandas DataFrame with combined historical data, or None if fetching fails.
    """
    logger.info(f"Fetching historical data for {symbol_spot} and {symbol_swap} on {exchange_id} for {lookback_days} days.")

    try:
        exchange = getattr(ccxt, exchange_id)({
            'enableRateLimit': True,
            # Add API keys if needed for fetching public data (usually not)
            # 'apiKey': OKX_API_KEY,
            # 'secret': OKX_SECRET_KEY,
            # 'password': OKX_PASSPHRASE,
            'options': {'defaultType': 'swap'}, # Default to swap for swap data
            # 'sandbox': OKX_SANDBOX,
        })

        exchange.load_markets()

        end_time_ms = exchange.milliseconds()
        start_time_ms = end_time_ms - lookback_days * 24 * 60 * 60 * 1000

        # Fetch historical funding rates (usually 3 times a day)
        # Need to fetch enough history to cover the lookback_days
        # OKX funding rates are usually every 8 hours, so 3 per day. lookback_days * 3 periods.
        # Let's fetch a bit more to be safe and filter later.
        funding_rates_list = []
        current_since = start_time_ms
        limit = 1000 # Max limit per call, adjust if needed based on exchange
        while True:
            logger.debug(f"Fetching funding rate history since {exchange.iso8601(current_since)}")
            rates_chunk = exchange.fetch_funding_rate_history(
                symbol_swap,
                since=current_since,
                limit=limit
            )
            if rates_chunk:
                funding_rates_list.extend(rates_chunk)
                # Update current_since to the timestamp of the last fetched item + 1ms
                current_since = rates_chunk[-1]['timestamp'] + 1
                # Break if we fetched less than limit (means no more data) or exceeded end_time
                if len(rates_chunk) < limit or rates_chunk[-1]['timestamp'] >= end_time_ms:
                    break
            else:
                break # No data returned

            time.sleep(exchange.rateLimit / 1000 + 0.1) # Respect rate limits

        if not funding_rates_list:
            logger.warning(f"No historical funding rate data fetched for {symbol_swap}.")
            return None

        df_funding = pd.DataFrame(funding_rates_list)
        df_funding['datetime'] = pd.to_datetime(df_funding['timestamp'], unit='ms')
        df_funding = df_funding[['datetime', 'fundingRate']]
        df_funding['fundingRate'] = pd.to_numeric(df_funding['fundingRate'])
        df_funding = df_funding.set_index('datetime').sort_index()

        # Fetch historical price data (e.g., 1-hour klines)
        # We need prices roughly around the funding rate settlement times (every 8 hours)
        # Fetching 1h klines and resampling might be a good approach.
        # Or fetch 8h klines if available and aligned with funding times.
        # Let's fetch 1h klines for both spot and swap and resample.
        timeframe = '1h'
        spot_ohlcv = exchange.fetch_ohlcv(symbol_spot, timeframe, start_time_ms)
        swap_ohlcv = exchange.fetch_ohlcv(symbol_swap, timeframe, start_time_ms)

        if not spot_ohlcv or not swap_ohlcv:
            logger.warning(f"Could not fetch historical OHLCV data for {symbol_spot} or {symbol_swap}.")
            return None

        df_spot = pd.DataFrame(spot_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_spot['datetime'] = pd.to_datetime(df_spot['timestamp'], unit='ms')
        df_spot = df_spot[['datetime', 'close']].set_index('datetime').sort_index()
        df_spot.rename(columns={'close': 'close_spot'}, inplace=True)

        df_swap = pd.DataFrame(swap_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_swap['datetime'] = pd.to_datetime(df_swap['timestamp'], unit='ms')
        df_swap = df_swap[['datetime', 'close']].set_index('datetime').sort_index()
        df_swap.rename(columns={'close': 'close_swap'}, inplace=True)

        # Combine dataframes
        # Merge funding rates with price data. Funding rates are sparse (3x a day).
        # We need prices *around* the funding rate timestamp.
        # A common approach is to use prices from the closest preceding kline.
        # Or resample price data to match funding rate frequency.
        # Let's resample price data to 8-hour intervals, taking the last close price.
        # Need to be careful about exact timing alignment with funding settlements.
        # A simpler approach for this example: merge funding rates and use forward fill for prices.
        # This assumes prices are relatively stable between funding settlements.

        # Merge funding rates with swap prices first
        df_combined = pd.merge(df_funding, df_swap, left_index=True, right_index=True, how='left')

        # Merge with spot prices
        df_combined = pd.merge(df_combined, df_spot, left_index=True, right_index=True, how='left')

        # Forward fill missing price data to align with funding rate timestamps
        df_combined[['close_swap', 'close_spot']] = df_combined[['close_swap', 'close_spot']].fillna(method='ffill')

        # Drop rows where prices are still missing (e.g., at the very beginning)
        df_combined = df_combined.dropna(subset=['close_swap', 'close_spot'])

        # Reset index to make datetime a column again
        df_combined = df_combined.reset_index()
        df_combined.rename(columns={'index': 'datetime'}, inplace=True)

        logger.info(f"Finished fetching and combining data. Shape: {df_combined.shape}")
        return df_combined

    except ccxt.NetworkError as e:
        logger.error(f"Network Error fetching historical data: {e}")
        return None
    except ccxt.ExchangeError as e:
        logger.error(f"Exchange Error fetching historical data: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred fetching historical data: {e}")
        return None

# --- Feature Engineering ---

def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates features for the ML model based on the article's description.

    Args:
        df: DataFrame with 'datetime', 'fundingRate', 'close_swap', 'close_spot' columns.

    Returns:
        DataFrame with added feature columns.
    """
    logger.info("Creating features...")

    df['price_diff'] = ((df['close_swap'] - df['close_spot']) / df['close_spot'] * 100).astype(float)
    df['prev_funding_rate'] = df['fundingRate'].shift(1)
    df['funding_ma3'] = df['fundingRate'].rolling(window=3).mean() # 3-period moving average
    df['hour'] = df['datetime'].dt.hour
    df['day_of_week'] = df['datetime'].dt.dayofweek # Monday=0, Sunday=6

    # The target variable is the *next* funding rate.
    # We need to shift the 'fundingRate' column *up* by 1 to get the next value for each row.
    df['next_funding_rate'] = df['fundingRate'].shift(-1)

    # Drop rows with NaN values created by shifting and rolling
    df = df.dropna()

    logger.info(f"Features created. DataFrame shape: {df.shape}")
    return df

# --- Model Training and Prediction ---

class FundingRatePredictor:
    """
    Handles training and prediction using a Linear Regression model.
    """
    def __init__(self, features: list, target: str = 'next_funding_rate'):
        self.features = features
        self.target = target
        self.model = LinearRegression()
        self.is_trained = False

    def train(self, df_train: pd.DataFrame):
        """
        Trains the Linear Regression model.

        Args:
            df_train: Training DataFrame with features and target.
        """
        logger.info("Training model...")
        X_train = df_train[self.features]
        y_train = df_train[self.target]

        self.model.fit(X_train, y_train)
        self.is_trained = True
        logger.info("Model training complete.")

    def predict(self, df_predict: pd.DataFrame) -> np.ndarray:
        """
        Makes predictions using the trained model.

        Args:
            df_predict: DataFrame with feature columns for prediction.

        Returns:
            Numpy array of predictions.
        """
        if not self.is_trained:
            logger.error("Model is not trained. Cannot make predictions.")
            return np.array([])

        X_predict = df_predict[self.features]
        predictions = self.model.predict(X_predict)
        return predictions

    def evaluate(self, df_test: pd.DataFrame):
        """
        Evaluates the model on the test set.

        Args:
            df_test: Test DataFrame with features and actual target.
        """
        if not self.is_trained:
            logger.error("Model is not trained. Cannot evaluate.")
            return

        logger.info("Evaluating model...")
        X_test = df_test[self.features]
        y_test = df_test[self.target]

        test_pred = self.model.predict(X_test)

        mse = mean_squared_error(y_test, test_pred)
        mae = mean_absolute_error(y_test, test_pred)
        r2 = r2_score(y_test, test_pred)

        logger.info("\nModel Evaluation:")
        logger.info(f"MSE: {mse:.10f}") # Use more precision for small values
        logger.info(f"MAE: {mae:.10f}")
        logger.info(f"R²: {r2:.6f}")

        # Feature Importance (for Linear Regression, coefficients indicate importance)
        coef_df = pd.DataFrame({
            'Feature': self.features,
            'Coefficient': self.model.coef_
        })
        logger.info("\nFeature Importance (Coefficients):")
        logger.info(coef_df.sort_values('Coefficient', key=abs, ascending=False))

        # Direction Accuracy (Predicting if the rate will be positive or negative)
        # Need to compare the sign of actual next funding rate and predicted next funding rate
        # Ensure both actual and predicted values are not zero for sign comparison
        actual_signs = np.sign(y_test[y_test != 0])
        predicted_signs = np.sign(test_pred[y_test != 0]) # Compare only where actual is not zero
        if len(actual_signs) > 0:
             direction_accuracy = np.mean(actual_signs == predicted_signs) * 100
             logger.info(f"\nDirection Accuracy (excluding zero actual rates): {direction_accuracy:.2f}%")
        else:
             logger.warning("No non-zero actual funding rates in test set to calculate direction accuracy.")


    def save_model(self, filepath: str):
        """Saves the trained model to a file."""
        if not self.is_trained:
            logger.warning("Model is not trained. Nothing to save.")
            return
        try:
            joblib.dump(self.model, filepath)
            logger.info(f"Model saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving model to {filepath}: {e}")

    def load_model(self, filepath: str):
        """Loads a trained model from a file."""
        try:
            if os.path.exists(filepath):
                self.model = joblib.load(filepath)
                self.is_trained = True
                logger.info(f"Model loaded from {filepath}")
            else:
                logger.warning(f"Model file not found at {filepath}. Model not loaded.")
        except Exception as e:
            logger.error(f"Error loading model from {filepath}: {e}")
            self.is_trained = False # Mark as not trained if loading fails


# --- Integration into the System Design ---

# How to integrate this ML component into the previously designed system:

# 1. DataProcessor (data_processor.py):
#    - Modify the update_market_data method to also fetch historical spot/swap prices
#      and recent funding rates needed for feature calculation (e.g., last few periods).
#    - Add a method to calculate the features for the *current* market state.
#    - Add a method to use the trained ML model to predict the *next* funding rate based on
#      the current market state features.
#    - Store the latest predicted funding rate.
#    - Provide a method (e.g., get_latest_predicted_funding_rate) for the Strategy module.

# 2. Strategy (strategy.py):
#    - Modify the check_open_signal method to use the predicted funding rate from
#      DataProcessor (e.g., self.data_proc.get_latest_predicted_funding_rate())
#      instead of or in addition to the exchange's next predicted funding rate (if available).
#    - Adjust the strategy parameters (e.g., min_annualized_funding_rate) to work with
#      the predicted values.
#    - The close signal logic might also consider the predicted funding rate turning unfavorable.

# 3. Main Program (main.py):
#    - In the initialization phase, load the trained ML model using FundingRatePredictor.load_model().
#    - Pass the FundingRatePredictor instance (or the prediction method) to DataProcessor.
#    - Ensure DataProcessor's data fetching and feature calculation logic runs frequently enough
#      to provide updated features for real-time prediction.
#    - Periodically re-train the model using recent historical data to keep it updated with market changes.
#      This could be a separate scheduled task (e.g., daily or weekly).

# --- Example Usage: Fetch Data, Train Model, Evaluate, Save/Load ---

if __name__ == "__main__":
    # 1. Fetch historical data
    total_lookback_days = LOOKBACK_DAYS_TRAIN + LOOKBACK_DAYS_TEST
    historical_df = fetch_historical_data(EXCHANGE_ID, SYMBOL_SPOT, SYMBOL_SWAP, total_lookback_days)

    if historical_df is None or historical_df.empty:
        logger.error("Failed to fetch enough historical data. Cannot proceed with ML.")
        exit()

    # 2. Create features
    df_with_features = create_features(historical_df.copy()) # Use a copy to avoid modifying original df

    if df_with_features.empty:
         logger.error("Failed to create features. DataFrame is empty after dropping NaNs.")
         exit()

    # 3. Define features and target
    # Ensure these features match the ones created in create_features
    features = ['prev_funding_rate', 'funding_ma3', 'price_diff', 'hour', 'day_of_week']
    target = 'next_funding_rate'

    # Check if all required features are present
    if not all(f in df_with_features.columns for f in features + [target]):
         logger.error(f"Required features or target column missing in DataFrame. Available columns: {df_with_features.columns}")
         exit()


    # 4. Split data into training and testing sets (time-based split as per article)
    # Find the split date
    split_date = df_with_features['datetime'].max() - datetime.timedelta(days=LOOKBACK_DAYS_TEST)
    df_train = df_with_features[df_with_features['datetime'] < split_date]
    df_test = df_with_features[df_with_features['datetime'] >= split_date]

    if df_train.empty or df_test.empty:
        logger.error("Training or test dataset is empty after splitting. Adjust lookback days or data fetching.")
        logger.info(f"Train data range: {df_train['datetime'].min()} to {df_train['datetime'].max()}")
        logger.info(f"Test data range: {df_test['datetime'].min()} to {df_test['datetime'].max()}")
        exit()

    logger.info(f"Training data shape: {df_train.shape}")
    logger.info(f"Test data shape: {df_test.shape}")


    # 5. Initialize and train the predictor
    predictor = FundingRatePredictor(features=features, target=target)
    predictor.train(df_train)

    # 6. Evaluate the model
    predictor.evaluate(df_test)

    # 7. Save the trained model
    predictor.save_model(MODEL_FILE)

    # 8. Example of loading the model later
    loaded_predictor = FundingRatePredictor(features=features, target=target)
    loaded_predictor.load_model(MODEL_FILE)

    # 9. Example prediction using the loaded model (e.g., on the last row of test data)
    if loaded_predictor.is_trained and not df_test.empty:
        last_data_point = df_test.tail(1)[features]
        if not last_data_point.empty:
             predicted_rate = loaded_predictor.predict(last_data_point)
             logger.info(f"\nExample Prediction on last test data point:")
             logger.info(f"Features: {last_data_point.iloc[0].to_dict()}")
             logger.info(f"Predicted Next Funding Rate: {predicted_rate[0]:.10f}")
             # Convert to annualized percentage for display
             predicted_ann_rate_pct = predicted_rate[0] * (3 * 365) * 100
             logger.info(f"Predicted Next Annualized Funding Rate: {predicted_ann_rate_pct:.4f}%")
        else:
             logger.warning("Test data is empty, cannot perform example prediction.")
    else:
         logger.warning("Model not loaded or test data empty, cannot perform example prediction.")

