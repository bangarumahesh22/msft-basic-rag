#!/bin/bash
# Deploy to Azure Container Apps using Docker Hub

# Load environment variables from .env file
[ -f .env ] && export $(grep -v '^#' .env | xargs)

# Configuration
RESOURCE_GROUP="rg-dev"
LOCATION="eastus"
ENVIRONMENT_NAME="rag-environment"
BACKEND_APP_NAME="rag-msft-backend"
FRONTEND_APP_NAME="rag-msft-frontend"
DOCKERHUB_USERNAME="u1800085"  # Replace with your Docker Hub username
REGISTRY_SERVER="docker.io"

# Set default values for missing environment variables
AZURE_SEARCH_INDEX_NAME=${AZURE_SEARCH_INDEX_NAME:-"documents-index"}
AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION:-"2023-05-15"}

# Prepare image names
IMAGE_BE="$DOCKERHUB_USERNAME/rag-msft-backend:latest"
IMAGE_FE="$DOCKERHUB_USERNAME/rag-msft-frontend:latest"

echo "Starting deployment process using Docker Hub..."

# Create Container Apps Environment (uncomment to create a new one)
# echo "Creating Container Apps Environment '$ENVIRONMENT_NAME'..."
# az containerapp env create --name "$ENVIRONMENT_NAME" --resource-group "$RESOURCE_GROUP" --location "$LOCATION"

# Prompt for Docker Hub credentials
echo "Please enter your Docker Hub username [default: $DOCKERHUB_USERNAME]:"
read input_username
[ -n "$input_username" ] && DOCKERHUB_USERNAME="$input_username" && IMAGE_BE="$DOCKERHUB_USERNAME/rag-msft-backend:latest" && IMAGE_FE="$DOCKERHUB_USERNAME/rag-msft-frontend:latest"

echo "Please enter your Docker Hub password:"
read -s DOCKERHUB_PASSWORD
echo

# Build and push images
echo "Logging in to Docker Hub and pushing images..."
echo "$DOCKERHUB_PASSWORD" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin
docker build -t "$IMAGE_BE" ./src/BE && docker push "$IMAGE_BE"
docker build -t "$IMAGE_FE" ./src/FE && docker push "$IMAGE_FE"

# Deploy backend app
echo "Deploying backend Container App '$BACKEND_APP_NAME'..."
az containerapp create \
  --name "$BACKEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENVIRONMENT_NAME" \
  --image "$IMAGE_BE" \
  --target-port 8000 \
  --ingress external \
  --registry-server "$REGISTRY_SERVER" \
  --registry-username "$DOCKERHUB_USERNAME" \
  --registry-password "$DOCKERHUB_PASSWORD" \
  --env-vars "AZURE_SEARCH_ENDPOINT=${AZURE_SEARCH_ENDPOINT}" \
             "AZURE_SEARCH_INDEX_NAME=${AZURE_SEARCH_INDEX_NAME}" \
             "AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}" \
             "AZURE_OPENAI_DEPLOYMENT_NAME=${AZURE_OPENAI_DEPLOYMENT_NAME}" \
             "AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION}"

# Add secrets for API keys
echo "Adding secure parameters for backend..."
az containerapp secret set \
  --name "$BACKEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --secrets "search-key=${AZURE_SEARCH_KEY}" "openai-key=${AZURE_OPENAI_KEY}"

az containerapp update \
  --name "$BACKEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --set-env-vars "AZURE_SEARCH_KEY=secretref:search-key" "AZURE_OPENAI_KEY=secretref:openai-key"

# Get backend URL and deploy frontend
BACKEND_URL=$(az containerapp show --name "$BACKEND_APP_NAME" --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" -o tsv)

echo "Deploying frontend Container App '$FRONTEND_APP_NAME'..."
az containerapp create \
  --name "$FRONTEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENVIRONMENT_NAME" \
  --image "$IMAGE_FE" \
  --target-port 8501 \
  --ingress external \
  --registry-server "$REGISTRY_SERVER" \
  --registry-username "$DOCKERHUB_USERNAME" \
  --registry-password "$DOCKERHUB_PASSWORD" \
  --env-vars "BACKEND_HOST=${BACKEND_URL}"

# Display deployment URLs
FRONTEND_URL=$(az containerapp show --name "$FRONTEND_APP_NAME" --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" -o tsv)

echo "Deployment complete!"
echo "Backend URL: https://$BACKEND_URL"
echo "Frontend URL: https://$FRONTEND_URL"