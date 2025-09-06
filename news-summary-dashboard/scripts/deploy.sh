#!/bin/bash

# Deploy script for production environment

echo "🚀 Starting deployment process..."

# Check if docker and docker-compose are installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if required .env files exist
if [ ! -f "./backend/.env" ]; then
    echo "Backend .env file not found. Please create ./backend/.env"
    exit 1
fi

if [ ! -f "./frontend/.env" ]; then
    echo "Frontend .env file not found. Please create ./frontend/.env"
    exit 1
fi

# Stop existing containers
echo "Stopping existing containers..."
docker-compose down

# Remove old images (optional)
echo "Cleaning up old images..."
docker system prune -f

# Build and start new containers
echo "Building and starting containers..."
docker-compose up --build -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 30

# Check if services are running
echo "Checking service health..."
if curl -f http://localhost:5000/api/health > /dev/null 2>&1; then
    echo "Backend is healthy"
else
    echo "Backend health check failed"
fi

if curl -f http://localhost:3000/health > /dev/null 2>&1; then
    echo "Frontend is healthy"
else
    echo "Frontend health check failed"
fi

# Show running containers
echo "Running containers:"
docker-compose ps

echo "Deployment complete!"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:5000"
