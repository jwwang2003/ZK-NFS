#!/bin/bash

# Define the file path and the target directory
TAR_FILE="./apache/apache-zookeeper-3.8.4-bin.tar.gz"
TARGET_DIR="./apache/apache-zookeeper-3.8.4-bin"

# Check if the tar.gz file exists
if [ ! -f "$TAR_FILE" ]; then
  echo "Error: $TAR_FILE not found."
  exit 1
fi

# Ensure the parent directory exists
mkdir -p "./apache"

# If the target folder already exists, skip extraction
if [ -d "$TARGET_DIR" ]; then
  echo "Directory $TARGET_DIR already exists; skipping extraction."
else
  echo "Extracting $TAR_FILE to ./apache..."
  tar -xzvf "$TAR_FILE" -C "./apache"
  if [ $? -ne 0 ]; then
    echo "Error: Failed to extract $TAR_FILE."
    exit 1
  fi
fi

# Verify zkCli.sh is present
if [ ! -f "$TARGET_DIR/bin/zkCli.sh" ]; then
  echo "Error: $TARGET_DIR/bin/zkCli.sh not found."
  exit 1
fi

# Run the ZooKeeper CLI
echo "Running ZooKeeper client..."
"$TARGET_DIR/bin/zkCli.sh" -server 127.0.0.1:2181
