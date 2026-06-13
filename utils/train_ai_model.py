import tensorflow as tf
from tensorflow.keras import layers, losses
from tensorflow.keras.models import Model
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import os
import pickle

# 1. Load Data
print("Loading datasets...")
train_df = pd.read_csv("data/train_normal.csv")
test_anomalies_df = pd.read_csv("data/test_anomalies.csv")

# 2. Preprocessing
# Scale all features between 0 and 1 for the Neural Network
scaler = MinMaxScaler()
train_data = scaler.fit_transform(train_df)
test_anomalies_data = scaler.transform(test_anomalies_df)

# Save the scaler for inference use later
if not os.path.exists("models"):
    os.makedirs("models")
with open("models/scaler.pkl", "wb") as f:
    pickle.dump(scaler, f)

# 3. Define the Autoencoder Architecture (Sequential)
# Using Sequential API avoids custom object serialization issues during TFLite conversion
autoencoder = tf.keras.Sequential([
    # Encoder
    tf.keras.Input(shape=(7,)),
    layers.Dense(16, activation="relu"),
    layers.Dense(8, activation="relu"),
    layers.Dense(4, activation="relu"),
    # Decoder
    layers.Dense(8, activation="relu"),
    layers.Dense(16, activation="relu"),
    layers.Dense(7, activation="sigmoid") # Sigmoid keeps output in [0,1] range
])

autoencoder.compile(optimizer='adam', loss='mae')

# 4. Training
print("Training the Autoencoder on 'Normal' data...")
history = autoencoder.fit(
    train_data, train_data, 
    epochs=50, 
    batch_size=32,
    validation_split=0.1,
    verbose=0 # Quiet training
)
print("Training complete.")

# 5. Determine Anomaly Threshold
# We calculate the mean absolute error on training samples
reconstructions = autoencoder.predict(train_data, verbose=0)
train_loss = tf.keras.losses.mae(reconstructions, train_data)
threshold = np.mean(train_loss) + np.std(train_loss)
print(f"Calculated Anomaly Threshold: {threshold:.4f}")

# 6. Save Model
# Save weights and architecture separately for better portability
autoencoder.save_weights("models/behavioral_ai_weights.weights.h5")
# Save the full model for TFLite conversion
autoencoder.save("models/behavioral_ai_full.keras")

# 7. Quick Test on Anomaly
reconstructions_ano = autoencoder.predict(test_anomalies_data, verbose=0)
test_loss_ano = tf.keras.losses.mae(reconstructions_ano, test_anomalies_data)
print(f"Average loss on anomalies: {np.mean(test_loss_ano):.4f}")

if np.mean(test_loss_ano) > threshold:
    print("SUCCESS: AI correctly identified synthetic anomalies!")
else:
    print("WARNING: Threshold might need tuning.")

with open("models/threshold.txt", "w") as f:
    f.write(str(threshold))
