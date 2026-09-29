# app/recon.py
# Surrounding info: WiFi, Bluetooth, LAN devices, Network
import subprocess
import re
import logging
import socket
from typing import List, Dict

logger = logging.getLogger("J.A.R.V.I.S")


def get_wifi_networks() -> List[Dict]:
    """Nearby WiFi networks via netsh (Windows)."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            capture_output=True, text=True, timeout=15,
        )
        networks = []
        current = {}
        for line in result.stdout.splitlines():
            s = line.strip()
            if s.startswith("SSID") and "BSSID" not in s:
                if current and current.get("ssid"):
                    networks.append(current)
                current = {"ssid": s.split(":", 1)[1].strip() if ":" in s else ""}
            elif s.startswith("Authentication"):
                current["auth"] = s.split(":", 1)[1].strip() if ":" in s else ""
            elif s.startswith("Signal"):
                current["signal"] = s.split(":", 1)[1].strip() if ":" in s else ""
        if current and current.get("ssid"):
            networks.append(current)
        return networks[:12]
    except Exception as e:
        logger.warning(f"WiFi scan failed: {e}")
        return []


def get_lan_devices() -> List[Dict]:
    """LAN devices via ARP table."""
    try:
        result = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=15)
        devices = []
        for line in result.stdout.splitlines():
            m = re.match(r"\s*(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F-]+)\s+(\w+)", line)
            if m:
                ip, mac, typ = m.groups()
                if ip.endswith(".255") or ip.startswith("224.") or ip.startswith("239."):
                    continue
                devices.append({"ip": ip, "mac": mac.replace("-", ":"), "type": typ})
        return devices[:25]
    except Exception as e:
        logger.warning(f"ARP failed: {e}")
        return []


def get_network_info() -> Dict:
    """Local IP + public IP + ISP."""
    info = {}
    try:
        info["local_ip"] = socket.gethostbyname(socket.gethostname())
    except Exception:
        info["local_ip"] = "unknown"
    try:
        import requests
        r = requests.get("https://ipapi.co/json/", timeout=6)
        if r.status_code == 200:
            d = r.json()
            info["public_ip"] = d.get("ip")
            info["city"] = d.get("city")
            info["region"] = d.get("region")
            info["country"] = d.get("country_name")
            info["isp"] = d.get("org")
    except Exception as e:
        logger.warning(f"IP info failed: {e}")
    return info


def get_bluetooth_devices() -> List[Dict]:
    """Nearby Bluetooth devices (Windows PowerShell)."""
    try:
        ps = ("Get-PnpDevice -Class Bluetooth | Where-Object {$_.Status -eq 'OK'} | "
              "Select-Object FriendlyName, InstanceId | ConvertTo-Json")
        result = subprocess.run(
            ["powershell", "-Command", ps],
            capture_output=True, text=True, timeout=20,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        import json
        data = json.loads(result.stdout)
        if isinstance(data, dict):
            data = [data]
        return [{"name": d.get("FriendlyName", "unknown"),
                 "id": d.get("InstanceId", "")} for d in data[:12]]
    except Exception as e:
        logger.warning(f"BT scan failed: {e}")
        return []