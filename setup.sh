#!/bin/bash
# setup.sh - Streamlit Cloud setup script

# Install packages from requirements.txt
pip install -r requirements.txt

# Create necessary directories
mkdir -p .streamlit

# Create config file
cat > .streamlit/config.toml << EOF
[server]
headless = true
enableCORS = false
enableXsrfProtection = false

[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
EOF
