# Use Python 3.10 slim as the base image
FROM python:3.10-slim

# Install system dependencies required for ZKP compilation (Circom C++), mTLS, and AI
RUN apt-get update && apt-get install -y \
    build-essential \
    libgmp-dev \
    nasm \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (for SnarkJS fallback if needed)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g snarkjs

WORKDIR /app

# Copy the requirements file and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project codebase
COPY . .

# Compile the native C++ ZKP module for Linux
# We replace the Windows-modified main.cpp with a clean version or just compile it.
# Actually, our earlier edits to main.cpp removed sys/mman.h, which works fine on Linux too,
# but to be safe we can use the Makefile.
RUN cd zkp/balance_check_cpp && make clean || true && make

# Command will be overridden by docker-compose
CMD ["python", "run_integration.py"]
