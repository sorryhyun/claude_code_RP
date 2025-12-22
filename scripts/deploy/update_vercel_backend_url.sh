#!/bin/bash
# Update Vercel environment variable with new cloudflared tunnel URL
# Usage: ./update_vercel_backend_url.sh [--no-redeploy]

set -e

REDEPLOY=true
if [ "$1" = "--no-redeploy" ]; then
    REDEPLOY=false
fi

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "Error: Vercel CLI not installed. Run: npm install -g vercel"
    exit 1
fi

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "Error: cloudflared not installed."
    exit 1
fi

# Create a temp file for cloudflared output
TUNNEL_OUTPUT=$(mktemp)
trap "rm -f $TUNNEL_OUTPUT" EXIT

echo "Starting cloudflared tunnel for backend..."

# Start cloudflared and capture output (port 8001 to avoid conflict with dev)
cloudflared tunnel --url http://localhost:8001 2>&1 | tee "$TUNNEL_OUTPUT" &
CLOUDFLARED_PID=$!

# Wait for the URL to appear (with timeout)
echo "Waiting for tunnel URL..."
TIMEOUT=30
ELAPSED=0
TUNNEL_URL=""

while [ $ELAPSED -lt $TIMEOUT ]; do
    # Look for the trycloudflare.com URL in the output
    TUNNEL_URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_OUTPUT" | head -1)

    if [ -n "$TUNNEL_URL" ]; then
        echo "Tunnel URL detected: $TUNNEL_URL"
        break
    fi

    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

if [ -z "$TUNNEL_URL" ]; then
    echo "Error: Could not detect tunnel URL within ${TIMEOUT}s"
    kill $CLOUDFLARED_PID 2>/dev/null || true
    exit 1
fi

# Update Vercel environment variable
echo ""
echo "Updating Vercel environment variable VITE_API_BASE_URL..."

# Remove existing env var (ignore error if it doesn't exist)
vercel env rm VITE_API_BASE_URL production -y 2>/dev/null || true

# Add new env var
echo "$TUNNEL_URL" | vercel env add VITE_API_BASE_URL production

echo "Environment variable updated successfully!"

# Trigger redeploy if requested
if [ "$REDEPLOY" = true ]; then
    echo ""
    echo "Triggering Vercel redeploy..."
    vercel --prod
    echo "Redeploy triggered!"
fi

echo ""
echo "=========================================="
echo "Backend tunnel URL: $TUNNEL_URL"
echo "=========================================="
echo ""
echo "Cloudflared is running in foreground. Press Ctrl+C to stop."
echo ""

# Wait for cloudflared (it's now in foreground)
wait $CLOUDFLARED_PID
