#!/bin/bash
echo "Starting..."

if ! docker-compose ps | grep -q "Up"; then
    echo "One or more containers are down. Restarting..."
    docker-compose up -d
else
    echo "Ok!"
fi
