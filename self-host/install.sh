#!/bin/bash
set -e

echo "=== LIDNS Installer ==="

# Install git if not present
if ! command -v git &>/dev/null; then
    echo "Installing git..."
    if command -v apt-get &>/dev/null; then
        apt-get update -q && apt-get install -y git
    elif command -v dnf &>/dev/null; then
        dnf install -y git
    elif command -v yum &>/dev/null; then
        yum install -y git
    elif command -v pacman &>/dev/null; then
        pacman -Sy --noconfirm git
    elif command -v zypper &>/dev/null; then
        zypper install -y git
    else
        echo "ERROR: Could not install git. Install it manually then re-run this script."
        exit 1
    fi
fi

# Clone or update
if [ -d "/root/lidns/.git" ]; then
    echo "Updating existing installation..."
    git -C /root/lidns pull
else
    echo "Cloning LIDNS..."
    git clone https://github.com/Sm0keSkreen/LIDNS.git /root/lidns
fi

chmod +x /root/lidns/self-host/setup.sh
bash /root/lidns/self-host/setup.sh
