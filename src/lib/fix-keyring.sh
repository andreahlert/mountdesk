#!/bin/bash
# MountDesk - Fix GNOME Keyring auto-unlock

echo "Opening Seahorse (Passwords and Keys)..."
echo ""
echo "If your keyring password differs from your login password:"
echo "  1. Right-click 'Login' → 'Change Password'"
echo "  2. Enter OLD keyring password"
echo "  3. Leave NEW password blank (or match login password)"
echo ""
seahorse &
