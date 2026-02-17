#!/bin/bash
# Quick installer for auto-deployment on production server
# Run this script on the production server to complete setup

echo "=========================================="
echo "🚀 Auto-Deployment Installer"
echo "=========================================="
echo

# Check if sudoers file exists
if [ ! -f /tmp/homeupdate-sudoers ]; then
    echo "❌ ERROR: /tmp/homeupdate-sudoers not found"
    echo "Please ensure you've pulled the latest code from GitHub first."
    exit 1
fi

# Step 1: Validate sudoers file
echo "Step 1: Validating sudoers configuration..."
sudo visudo -c -f /tmp/homeupdate-sudoers
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Sudoers file has syntax errors. Aborting."
    exit 1
fi
echo "✓ Sudoers file is valid"
echo

# Step 2: Install sudoers file
echo "Step 2: Installing sudoers configuration..."
sudo cp /tmp/homeupdate-sudoers /etc/sudoers.d/homeupdate
sudo chmod 440 /etc/sudoers.d/homeupdate
echo "✓ Sudoers configuration installed"
echo

# Step 3: Verify permissions
echo "Step 3: Verifying sudo permissions..."
if sudo -l | grep -q homeupdate; then
    echo "✓ Sudo permissions successfully configured"
else
    echo "⚠️  WARNING: Could not verify sudo permissions. Check manually."
fi
echo

# Step 4: Test script execution
echo "Step 4: Testing auto-deployment script..."
if [ -x /home/zakee/homeupdate/auto_deploy.sh ]; then
    echo "✓ Script is executable"
else
    echo "❌ ERROR: Script is not executable"
    chmod +x /home/zakee/homeupdate/auto_deploy.sh
    echo "✓ Fixed: Made script executable"
fi
echo

# Step 5: Cron setup instructions
echo "=========================================="
echo "✅ Installation Complete!"
echo "=========================================="
echo
echo "Next step: Setup cron job"
echo "Run: crontab -e"
echo
echo "Add one of these lines:"
echo
echo "# Every day at 3:00 AM:"
echo "0 3 * * * /home/zakee/homeupdate/auto_deploy.sh >> /home/zakee/homeupdate/logs/cron.log 2>&1"
echo
echo "# Every 6 hours:"
echo "0 */6 * * * /home/zakee/homeupdate/auto_deploy.sh >> /home/zakee/homeupdate/logs/cron.log 2>&1"
echo
echo "Test the script manually first:"
echo "/home/zakee/homeupdate/auto_deploy.sh"
echo
