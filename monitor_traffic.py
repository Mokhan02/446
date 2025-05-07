#!/usr/bin/env python3
import subprocess
import logging
import time
import json
from typing import Dict
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WindowsTrafficMonitor:
    def __init__(self):
        self.interface = "Ethernet"  # Default interface name
        self.sample_interval = 1  # seconds
        self.config_path = "priority.json"
        self.priority_config = self._load_config()

    def _load_config(self) -> Dict:
        """Load and normalize the priority configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                raw_config = json.load(f)
                # Convert list to a dict with app name keys for easy lookup
                app_to_level = {}
                for level in raw_config.get("priority_levels", []):
                    level_name = level["name"]
                    for app in level.get("applications", []):
                        normalized = app["name"].lower().replace(" ", "")
                        app_to_level[f"Auto_{normalized}"] = level_name
                return app_to_level
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in configuration file: {self.config_path}")
            return {}

    def get_qos_stats(self) -> Dict:
        """Get QoS policy statistics using PowerShell."""
        try:
            ps_command = (
                "Get-NetQosPolicy | Select-Object Name, ThrottleRateActionBitsPerSecond, "
                "@{Name='Bytes';Expression={(Get-Counter \"\\Network Interface(*)\\Bytes Total/sec\").CounterSamples.CookedValue}} | ConvertTo-Json"
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                check=True
            )
            return self._parse_qos_output(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get QoS stats: {e}")
            return {}

    def _parse_qos_output(self, output: str) -> Dict:
        """Parse PowerShell QoS output."""
        stats = {}
        try:
            qos_data = json.loads(output)
            if isinstance(qos_data, dict):  # Single object case
                qos_data = [qos_data]

            for policy in qos_data:
                policy_name = policy["Name"]
                level_name = self.priority_config.get(policy_name)
                if not level_name:
                    continue
                if level_name not in stats:
                    stats[level_name] = {"bytes": 0, "bandwidth": 0}
                stats[level_name]["bytes"] += policy.get("Bytes", 0)
                stats[level_name]["bandwidth"] = policy.get("ThrottleRateActionBitsPerSecond", 0) / 1_000_000
        except json.JSONDecodeError:
            logger.error("Failed to parse QoS statistics")
        return stats

    def get_interface_stats(self) -> Dict:
        """Get interface statistics using PowerShell."""
        try:
            ps_command = (
                "Get-NetAdapterStatistics -Name \"Ethernet\" | "
                "Select-Object ReceivedBytes, SentBytes | ConvertTo-Json"
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                check=True
            )
            return self._parse_interface_output(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get interface stats: {e}")
            return {}

    def _parse_interface_output(self, output: str) -> Dict:
        """Parse PowerShell interface statistics output."""
        stats = {
            "input_bytes": 0,
            "output_bytes": 0
        }
        try:
            data = json.loads(output)
            stats["input_bytes"] = data.get("ReceivedBytes", 0)
            stats["output_bytes"] = data.get("SentBytes", 0)
        except json.JSONDecodeError:
            logger.error("Failed to parse interface statistics")
        return stats

    def monitor(self, duration: int = 60) -> None:
        """Monitor traffic for the specified duration."""
        logger.info(f"Starting traffic monitoring for {duration} seconds...")

        start_time = time.time()
        while time.time() - start_time < duration:
            qos_stats = self.get_qos_stats()
            interface_stats = self.get_interface_stats()

            print("\nTraffic Statistics:")
            print("------------------")
            for level_name, data in qos_stats.items():
                print(f"\n{level_name} Priority (Bandwidth: {data['bandwidth']} MB/s)")
                print(f"  Bytes: {data['bytes']}")

            print("\nInterface Statistics:")
            print(f"  Input Bytes: {interface_stats['input_bytes']}")
            print(f"  Output Bytes: {interface_stats['output_bytes']}")

            total_bytes = sum(level["bytes"] for level in qos_stats.values())
            if total_bytes > 0:
                print("\nBandwidth Allocation:")
                for level_name, level_stats in qos_stats.items():
                    percent = (level_stats["bytes"] / total_bytes * 100)
                    print(f"  {level_name}: {percent:.2f}% (Target: {level_stats['bandwidth']} MB/s)")

            time.sleep(self.sample_interval)

def main():
    monitor = WindowsTrafficMonitor()
    try:
        monitor.monitor()
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        logger.error(f"Error during monitoring: {e}")

if __name__ == "__main__":
    main()
