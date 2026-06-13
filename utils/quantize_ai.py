import tensorflow as tf
import pandas as pd
import numpy as np
import os
import pickle

print("Loading the full Keras model...")
model = tf.keras.models.load_model("models/behavioral_ai_full.keras")

# Load training data to use as a representative dataset for quantization
print("Loading representative dataset for INT8 quantization...")
train_df = pd.read_csv("data/train_normal.csv")
with open("models/scaler.pkl", "rb") as f:
    scaler = pickle.load(f)
train_data = scaler.transform(train_df)

def representative_data_gen():
    """Yields small batches of data for the converter to calibrate the INT8 ranges."""
    for i in range(100):
        # Provide a small batch of 1 sample
        data = train_data[i:i+1].astype(np.float32)
        yield [data]

print("Initializing TFLite Converter...")
converter = tf.lite.TFLiteConverter.from_keras_model(model)

# Apply INT8 Quantization (Priority 3 Optimization)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = representative_data_gen

# Ensure that if any ops can't be quantized, the converter throws an error 
# rather than falling back to float, to guarantee maximum performance.
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8

print("Converting model to INT8 TFLite format...")
try:
    tflite_quant_model = converter.convert()
    
    # Save the quantized model
    tflite_model_path = "models/behavioral_ai_quantized.tflite"
    with open(tflite_model_path, "wb") as f:
        f.write(tflite_quant_model)
    
    # Compare sizes
    keras_size = os.path.getsize("models/behavioral_ai_full.keras")
    tflite_size = os.path.getsize(tflite_model_path)
    
    print("\n--- Quantization Complete ---")
    print(f"Original Keras Model Size: {keras_size / 1024:.2f} KB")
    print(f"INT8 TFLite Model Size:    {tflite_size / 1024:.2f} KB")
    print(f"Size Reduction:            {(1 - (tflite_size/keras_size)) * 100:.1f}%")
    print(f"Saved to: {tflite_model_path}")
except Exception as e:
    print(f"Error during quantization: {e}")
