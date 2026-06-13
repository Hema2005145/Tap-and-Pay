import flwr as fl
import tensorflow as tf
from tensorflow.keras import layers
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import os
import sys

# Change directory so data paths are correct
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def load_data():
    # Load and scale local data (simulating edge device's private data)
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "train_normal.csv")
    df = pd.read_csv(data_path)
    
    # We slice to simulate different data sets for different clients
    # For demo purposes, we will just sample half the data randomly
    df = df.sample(frac=0.5, random_state=int.from_bytes(os.urandom(4), 'big')) 
    
    scaler = MinMaxScaler()
    data = scaler.fit_transform(df)
    return data

def build_model():
    model = tf.keras.Sequential([
        tf.keras.Input(shape=(7,)),
        layers.Dense(16, activation="relu"),
        layers.Dense(8, activation="relu"),
        layers.Dense(4, activation="relu"),
        layers.Dense(8, activation="relu"),
        layers.Dense(16, activation="relu"),
        layers.Dense(7, activation="sigmoid")
    ])
    model.compile(optimizer='adam', loss='mae')
    return model

class PaymentClient(fl.client.NumPyClient):
    def __init__(self, model, train_data):
        self.model = model
        self.train_data = train_data

    def get_parameters(self, config):
        return self.model.get_weights()

    def fit(self, parameters, config):
        self.model.set_weights(parameters)
        self.model.fit(self.train_data, self.train_data, epochs=3, batch_size=32, verbose=0)
        return self.model.get_weights(), len(self.train_data), {}

    def evaluate(self, parameters, config):
        self.model.set_weights(parameters)
        loss = self.model.evaluate(self.train_data, self.train_data, verbose=0)
        return float(loss), len(self.train_data), {"mae": float(loss)}

def main():
    print("Federated Learning [Flower Client]: Loading local transaction data...")
    train_data = load_data()
    print(f"Data loaded: {len(train_data)} local device samples.")
    
    model = build_model()
    
    # Pre-load existing global model if we have it
    model_path = os.path.join(os.path.dirname(__file__), "..", "models", "behavioral_ai_weights.weights.h5")
    if os.path.exists(model_path):
        model.load_weights(model_path)
    
    print("Federated Learning [Flower Client]: Connecting to Aggregation Server...")
    # Start Flower client using NumPyClient (which uses start_client under the hood properly depending on flower version)
    # Using fl.client.start_client directly
    fl.client.start_client(
        server_address="127.0.0.1:9091",
        client=PaymentClient(model, train_data).to_client()
    )

if __name__ == "__main__":
    main()
