#!/bin/bash
# Deploy to Azure Container Apps

# Configuration
RESOURCE_GROUP="rg-dev"
LOCATION="eastus"
ENVIRONMENT_NAME="rag-environment"
BACKEND_APP_NAME="rag-backend"
FRONTEND_APP_NAME="rag-frontend"

# Registry choice (uncomment one)
# Option 1: Docker Hub
REGISTRY_SERVER="docker.io"
REGISTRY_USERNAME="u1800085"  # Replace with your Docker Hub username
IMAGE_BE="$REGISTRY_USERNAME/rag-msft-backend:latest"
IMAGE_FE="$REGISTRY_USERNAME/rag-msft-frontend:latest"

# Option 2: Azure Container Registry (uncomment these lines and comment out Docker Hub options above)
# ACR_NAME="ragsystemacr"  # Must be globally unique
# REGISTRY_SERVER="$ACR_NAME.azurecr.io"
# IMAGE_BE="$REGISTRY_SERVER/rag-backend:latest"
# IMAGE_FE="$REGISTRY_SERVER/rag-frontend:latest"

echo "Starting deployment process..."

# Create resource group
# echo "Creating resource group '$RESOURCE_GROUP' in '$LOCATION'..."
# az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

# Create Container Apps Environment
echo "Creating Container Apps Environment '$ENVIRONMENT_NAME'..."
az containerapp env create \
  --name "$ENVIRONMENT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION"

# If using Azure Container Registry, create and log in
if [[ "$REGISTRY_SERVER" == *"azurecr.io"* ]]; then
  echo "Creating Azure Container Registry '$ACR_NAME'..."
  az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACR_NAME" \
    --sku Basic \
    --admin-enabled true
  
  # Get credentials
  ACR_USERNAME=$(az acr credential show -n "$ACR_NAME" --query "username" -o tsv)
  ACR_PASSWORD=$(az acr credential show -n "$ACR_NAME" --query "passwords[0].value" -o tsv)
  
  # Log in to ACR
  echo "Logging in to ACR..."
  docker login "$REGISTRY_SERVER" -u "$ACR_USERNAME" -p "$ACR_PASSWORD"
  
  # Set registry credentials for Container Apps
  REGISTRY_USERNAME="$ACR_USERNAME"
  REGISTRY_PASSWORD="$ACR_PASSWORD"
else
  # For Docker Hub, prompt for password
  echo "Please enter your Docker Hub password for $REGISTRY_USERNAME:"
  read -s REGISTRY_PASSWORD
fi

# Build and push images
echo "Building and pushing backend image..."
docker build -t "$IMAGE_BE" ./src/BE
docker push "$IMAGE_BE"

echo "Building and pushing frontend image..."
docker build -t "$IMAGE_FE" ./src/FE
docker push "$IMAGE_FE"

# Create secret for registry credentials
echo "Creating registry credentials in Container Apps Environment..."
az containerapp registry set \
  --name "$ENVIRONMENT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --server "$REGISTRY_SERVER" \
  --username "$REGISTRY_USERNAME" \
  --password "$REGISTRY_PASSWORD"

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
  --env-vars "AZURE_SEARCH_ENDPOINT=${AZURE_SEARCH_ENDPOINT}" \
             "AZURE_SEARCH_INDEX_NAME=${AZURE_SEARCH_INDEX_NAME}" \
             "AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}" \
             "AZURE_OPENAI_DEPLOYMENT_NAME=${AZURE_OPENAI_DEPLOYMENT_NAME}" \
             "AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION}"

# Create secure parameters for keys
echo "Adding secure parameters for backend..."
az containerapp secret set \
  --name "$BACKEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --secrets "search-key=${AZURE_SEARCH_KEY}" "openai-key=${AZURE_OPENAI_KEY}"

# Update backend with secure parameters
az containerapp update \
  --name "$BACKEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --set-env-vars "AZURE_SEARCH_KEY=secretref:search-key" "AZURE_OPENAI_KEY=secretref:openai-key"

# Get backend URL
BACKEND_URL=$(az containerapp show \
  --name "$BACKEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" -o tsv)

# Deploy frontend app
echo "Deploying frontend Container App '$FRONTEND_APP_NAME'..."
az containerapp create \
  --name "$FRONTEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENVIRONMENT_NAME" \
  --image "$IMAGE_FE" \
  --target-port 8501 \
  --ingress external \
  --registry-server "$REGISTRY_SERVER" \
  --env-vars "BACKEND_HOST=https://${BACKEND_URL}" "BACKEND_PORT=443"

# Get frontend URL
FRONTEND_URL=$(az containerapp show \
  --name "$FRONTEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" -o tsv)

echo "Deployment complete!"
echo "Backend URL: https://$BACKEND_URL"
echo "Frontend URL: https://$FRONTEND_URL"