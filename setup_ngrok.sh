#!/bin/bash
# ngrok Installation Script for WSL Ubuntu

echo "🔧 Installing ngrok..."

# Download ngrok for Linux
cd ~
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz

# Extract
tar -xzf ngrok-v3-stable-linux-amd64.tgz

# Move to /usr/local/bin
sudo mv ngrok /usr/local/bin/

# Clean up
rm ngrok-v3-stable-linux-amd64.tgz

echo "✅ ngrok installed successfully!"
echo ""
echo "⚙️  Next steps:"
echo "1. Sign up for ngrok at https://ngrok.com/"
echo "2. Get your auth token from https://dashboard.ngrok.com/get-started/your-authtoken"
echo "3. Run: ngrok config add-authtoken YOUR_AUTH_TOKEN"
echo ""
