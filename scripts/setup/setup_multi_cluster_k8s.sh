#!/usr/bin/env bash

set -e

echo "================================================"
echo "Multi-Cluster Kubernetes MCP Setup"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}✗ kubectl not found. Please install kubectl first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ kubectl found${NC}"

# Check gcloud (optional)
if ! command -v gcloud &> /dev/null; then
    echo -e "${YELLOW}⚠ gcloud not found. You'll need to configure clusters manually.${NC}"
    HAVE_GCLOUD=false
else
    echo -e "${GREEN}✓ gcloud found${NC}"
    HAVE_GCLOUD=true
fi

echo ""
echo "This script will help you set up multiple GKE clusters for MCP access."
echo ""

# Ask about clusters
echo "Enter your cluster details:"
echo "(Press Enter to skip any cluster)"
echo ""

declare -A CLUSTERS

read -p "Development cluster name (e.g., dev-cluster): " DEV_CLUSTER
if [ -n "$DEV_CLUSTER" ]; then
    read -p "Development cluster region (e.g., asia-south1): " DEV_REGION
    read -p "Development GCP project ID: " DEV_PROJECT
    CLUSTERS["dev"]="$DEV_PROJECT:$DEV_CLUSTER:$DEV_REGION"
fi

read -p "UAT cluster name (optional): " UAT_CLUSTER
if [ -n "$UAT_CLUSTER" ]; then
    read -p "UAT cluster region (e.g., asia-south1): " UAT_REGION
    read -p "UAT GCP project ID: " UAT_PROJECT
    CLUSTERS["uat"]="$UAT_PROJECT:$UAT_CLUSTER:$UAT_REGION"
fi

# read -p "Staging cluster name (e.g., staging-cluster): " STAGING_CLUSTER
# if [ -n "$STAGING_CLUSTER" ]; then
#     read -p "Staging cluster region (e.g., asia-south1): " STAGING_REGION
#     read -p "Staging GCP project ID: " STAGING_PROJECT
#     CLUSTERS["staging"]="$STAGING_PROJECT:$STAGING_CLUSTER:$STAGING_REGION"
# fi

# read -p "Production cluster name (e.g., prod-cluster): " PROD_CLUSTER
# if [ -n "$PROD_CLUSTER" ]; then
#     read -p "Production cluster region (e.g., asia-south1): " PROD_REGION
#     read -p "Production GCP project ID: " PROD_PROJECT
#     CLUSTERS["prod"]="$PROD_PROJECT:$PROD_CLUSTER:$PROD_REGION"
# fi


echo ""
echo "================================================"
echo "Cluster Summary"
echo "================================================"
for env in "${!CLUSTERS[@]}"; do
    IFS=':' read -r project cluster region <<< "${CLUSTERS[$env]}"
    echo "$env: $cluster ($region) [project: $project]"
done
echo ""

read -p "Proceed with setup? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "Setup cancelled."
    exit 0
fi

echo ""
echo "================================================"
echo "Step 1: Getting cluster credentials"
echo "================================================"

if [ "$HAVE_GCLOUD" = true ]; then
    for env in "${!CLUSTERS[@]}"; do
        IFS=':' read -r project cluster region <<< "${CLUSTERS[$env]}"
        echo "Getting credentials for $cluster..."
        
        if gcloud container clusters get-credentials "$cluster" \
            --region "$region" --project "$project" 2>/dev/null; then
            echo -e "${GREEN}✓ $cluster credentials obtained${NC}"
        else
            echo -e "${YELLOW}⚠ Failed to get credentials for $cluster${NC}"
        fi
    done
else
    echo -e "${YELLOW}Skipping credential fetch (gcloud not available)${NC}"
    echo "Please run these commands manually:"
    for env in "${!CLUSTERS[@]}"; do
        IFS=':' read -r cluster region <<< "${CLUSTERS[$env]}"
        echo "  gcloud container clusters get-credentials $cluster --region $region"
    done
fi

echo ""
echo "================================================"
echo "Step 2: Listing current contexts"
echo "================================================"
kubectl config get-contexts
echo ""

echo "================================================"
echo "Step 3: Renaming contexts"
echo "================================================"

for env in "${!CLUSTERS[@]}"; do
    IFS=':' read -r cluster region <<< "${CLUSTERS[$env]}"
    
    # Try to find the context name
    # GKE format: gke_project_region_cluster
    FULL_CONTEXT="gke_${project}_${region}_${cluster}"
    
    echo "Renaming $FULL_CONTEXT to $env..."
    
    if kubectl config rename-context "$FULL_CONTEXT" "$env" 2>/dev/null; then
        echo -e "${GREEN}✓ Renamed to $env${NC}"
    else
        # Try alternate format
        ALT_CONTEXT="gke_${GCP_PROJECT}_${region//-/_}_${cluster}"
        if kubectl config rename-context "$ALT_CONTEXT" "$env" 2>/dev/null; then
            echo -e "${GREEN}✓ Renamed to $env${NC}"
        else
            echo -e "${YELLOW}⚠ Could not rename $FULL_CONTEXT${NC}"
            echo "  You may need to rename manually:"
            echo "  kubectl config rename-context <actual-name> $env"
        fi
    fi
done

echo ""
echo "================================================"
echo "Step 4: Verifying contexts"
echo "================================================"
kubectl config get-contexts
echo ""

echo "================================================"
echo "Step 5: Testing cluster access"
echo "================================================"

for env in "${!CLUSTERS[@]}"; do
    echo "Testing $env cluster..."
    if kubectl --context="$env" cluster-info >/dev/null 2>&1; then
        echo -e "${GREEN}✓ $env cluster is accessible${NC}"
    else
        echo -e "${RED}✗ $env cluster is not accessible${NC}"
    fi
done

echo ""
echo "================================================"
echo "Step 6: Creating kubeconfig backup"
echo "================================================"

BACKUP_FILE="$HOME/.kube/config.backup.$(date +%Y%m%d_%H%M%S)"
cp "$HOME/.kube/config" "$BACKUP_FILE"
echo -e "${GREEN}✓ Backup created: $BACKUP_FILE${NC}"

echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Update k8s_multi_cluster_mcp.py with your context names:"
echo "   CONTEXTS = {"
for env in "${!CLUSTERS[@]}"; do
    echo "       \"$env\": \"$env\","
done
echo "   }"
echo ""
echo "2. Update your Claude Desktop config:"
echo "   {"
echo "     \"mcpServers\": {"
echo "       \"kubernetes\": {"
echo "         \"command\": \"python\","
echo "         \"args\": [\"/path/to/k8s_multi_cluster_mcp.py\"]"
echo "       }"
echo "     }"
echo "   }"
echo ""
echo "3. Restart Claude Desktop"
echo ""
echo "4. Test by asking Claude:"
echo "   'Show me pods in staging cluster'"
echo "   'List deployments in production'"
echo ""
echo -e "${GREEN}Setup complete! 🚀${NC}"