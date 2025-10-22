#!/bin/bash
# Deploy to Azure Container Apps using Azure Container Registry

# Configuration
RESOURCE_GROUP="rag-system-rg"
LOCATION="eastus"
ENVIRONMENT_NAME="rag-environment"
BACKEND_APP_NAME="rag-backend"
FRONTEND_APP_NAME="rag-frontend"

# Azure Container Registry Configuration
ACR_NAME="ragsystemacr"  # Must be globally unique, change this!
REGISTRY_SERVER="$ACR_NAME.azurecr.io"
IMAGE_BE="$REGISTRY_SERVER/rag-backend:latest"
IMAGE_FE="$REGISTRY_SERVER/rag-frontend:latest"

echo "Starting deployment process using Azure Container Registry..."

if [ "$BUILD_ONLY" = true ]; then
    echo "Building images locally and preparing for manual push to Azure Container Registry later..."
    echo "Note: Since Azure CLI is not installed, we'll prepare the images but not push them."
    
    # Set dummy values for local builds
    ACR_USERNAME="dummy"
    ACR_PASSWORD="dummy"
    
    # Build images with full ACR tags but don't push
    echo "Building backend image tagged as '$IMAGE_BE'..."
    docker build -t "$IMAGE_BE" ./src/BE
    
    echo "Building frontend image tagged as '$IMAGE_FE'..."
    docker build -t "$IMAGE_FE" ./src/FE
    
    echo "\nImages built successfully. To push them to ACR later:"
    echo "1. Install Azure CLI"
    echo "2. Log in to Azure: az login"
    echo "3. Create an Azure Container Registry"
    echo "4. Log in to your ACR: az acr login --name your-acr-name"
    echo "5. Tag and push your images: "
    echo "   docker push $IMAGE_BE"
    echo "   docker push $IMAGE_FE"
    exit 0
fi

# Create resource group
echo "Creating resource group '$RESOURCE_GROUP' in '$LOCATION'..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

# Create Azure Container Registry
echo "Creating Azure Container Registry '$ACR_NAME'..."
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled true

# Get ACR credentials
echo "Getting ACR credentials..."
ACR_USERNAME=$(az acr credential show -n "$ACR_NAME" --query "username" -o tsv)
ACR_PASSWORD=$(az acr credential show -n "$ACR_NAME" --query "passwords[0].value" -o tsv)

# Log in to ACR
echo "Logging in to ACR..."
echo "$ACR_PASSWORD" | docker login "$REGISTRY_SERVER" -u "$ACR_USERNAME" --password-stdin

# Create Container Apps Environment
echo "Creating Container Apps Environment '$ENVIRONMENT_NAME'..."
az containerapp env create \
  --name "$ENVIRONMENT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION"

# Build and push images
echo "Building and pushing backend image to ACR..."
docker build -t "$IMAGE_BE" ./src/BE
docker push "$IMAGE_BE"

echo "Building and pushing frontend image to ACR..."
docker build -t "$IMAGE_FE" ./src/FE
docker push "$IMAGE_FE"

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
  --registry-username "$ACR_USERNAME" \
  --registry-password "$ACR_PASSWORD" \
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
  --registry-username "$ACR_USERNAME" \
  --registry-password "$ACR_PASSWORD" \
  --env-vars "BACKEND_HOST=https://${BACKEND_URL}" "BACKEND_PORT=443"

# Get frontend URL
FRONTEND_URL=$(az containerapp show \
  --name "$FRONTEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" -o tsv)

echo "Deployment complete!"
echo "Backend URL: https://$BACKEND_URL"
echo "Frontend URL: https://$FRONTEND_URL"
echo "Azure Container Registry: $REGISTRY_SERVER"