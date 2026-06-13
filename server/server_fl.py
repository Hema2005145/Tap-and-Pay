import flwr as fl

# Define the strategy for aggregation (FedAvg)
strategy = fl.server.strategy.FedAvg(
    fraction_fit=1.0,  # Sample 100% of available clients for training
    fraction_evaluate=1.0,  # Sample 100% of available clients for evaluation
    min_fit_clients=2,  # Minimum number of clients to be sampled for next round
    min_evaluate_clients=2,  # Minimum number of clients to be sampled for evaluation
    min_available_clients=2,  # Wait until at least 2 clients are available
)

def main():
    print("Federated Learning [Flower Server]: Starting Aggregation Server on 0.0.0.0:9091...")
    fl.server.start_server(
        server_address="0.0.0.0:9091",
        config=fl.server.ServerConfig(num_rounds=3),
        strategy=strategy,
    )

if __name__ == "__main__":
    main()
