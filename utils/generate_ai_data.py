import numpy as np
import pandas as pd
import os

def generate_behavioral_data(num_samples=1000, is_anomaly=False):
    """
    Generates synthetic behavioral data for a 'Tap-and-Pay' scenario.
    Normal: Consistent tilt, regular amounts, specific GPS cluster.
    Anomaly: Random tilt, unusual amounts, random GPS.
    """
    np.random.seed(42 if not is_anomaly else 7)
    
    # 1. Amount (Cents)
    if not is_anomaly:
        # Normal: Small to medium payments (coffee, groceries)
        amounts = np.random.normal(2500, 1000, num_samples).clip(500, 10000)
    else:
        # Anomaly: Large, unusual payments
        amounts = np.random.uniform(20000, 100000, num_samples)

    # 2. GPS Location (Latitude, Longitude) - Centered around a 'Home' city
    home_lat, home_lon = 12.9716, 77.5946 # Bangalore example
    if not is_anomaly:
        lat = np.random.normal(home_lat, 0.01, num_samples)
        lon = np.random.normal(home_lon, 0.01, num_samples)
    else:
        lat = np.random.uniform(-90, 90, num_samples)
        lon = np.random.uniform(-180, 180, num_samples)

    # 3. Device Tilt (X, Y, Z) - Accelerometer data during a natural tap
    if not is_anomaly:
        # Normal: Phone held at a roughly 45-degree angle (0.7 in radians)
        tilt_x = np.random.normal(0.7, 0.1, num_samples)
        tilt_y = np.random.normal(0.2, 0.05, num_samples)
        tilt_z = np.random.normal(0.9, 0.1, num_samples)
    else:
        # Anomaly: Erratic movement or flat on a table (automated bot tap)
        tilt_x = np.random.uniform(-1, 1, num_samples)
        tilt_y = np.random.uniform(-1, 1, num_samples)
        tilt_z = np.random.uniform(-1, 1, num_samples)

    # 4. Timestamp (Hour of day)
    if not is_anomaly:
        # Normal: Daytime hours (8 AM to 10 PM)
        hours = np.random.normal(15, 4, num_samples).clip(0, 23)
    else:
        # Anomaly: Middle of the night (2 AM to 4 AM)
        hours = np.random.uniform(2, 4, num_samples)

    df = pd.DataFrame({
        'amount': amounts,
        'lat': lat,
        'lon': lon,
        'tilt_x': tilt_x,
        'tilt_y': tilt_y,
        'tilt_z': tilt_z,
        'hour': hours
    })
    
    return df

if __name__ == "__main__":
    print("Generating training data (Normal)...")
    train_data = generate_behavioral_data(5000, is_anomaly=False)
    
    print("Generating testing data (Anomalies)...")
    test_anomalies = generate_behavioral_data(500, is_anomaly=True)
    
    # Save to CSV for the next step
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    train_data.to_csv(f"{data_dir}/train_normal.csv", index=False)
    test_anomalies.to_csv(f"{data_dir}/test_anomalies.csv", index=False)
    
    print(f"Data saved to {data_dir}/. Ready for Autoencoder training.")
