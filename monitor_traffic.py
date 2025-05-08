#!/usr/bin/env python3
import subprocess
import logging
import time
import json
from typing import Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("traffic_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WindowsTrafficMonitor:
    def __init__(self):
        self.interface = self.detect_interface()  # Dynamically detect interface
        self.sample_interval = 1  # seconds
        self.config_path = "priority.json"
        self.priority_config = self._load_config()

    def detect_interface(self) -> str:
        """Detect the active network interface."""
        try:
            ps_command = (
                "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | "
                "Select-Object -First 1 Name | ForEach-Object {$_.Name}"
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                check=True
            )
            interface = result.stdout.strip()
            if not interface:
                logger.warning("No active network interface found. Using default 'Ethernet'.")
                return "Ethernet"
            logger.info(f"Detected active interface: {interface}")
            return interface
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to detect network interface: {e.stderr}")
            return "Ethernet"

    def _load_config(self) -> Dict:
        """Load and normalize the priority configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                raw_config = json.load(f)
                app_to_level = {}
                app_mapping = {
                    "zoom.exe": "Zoom",
                    "discord.exe": "Discord Voice",
                    "valorant.exe": "Valorant",
                    "steam.exe": "Steam"
                }
                for level in raw_config.get("priority_levels", []):
                    level_name = level["name"]
                    for app in level.get("applications", []):
                        app_name = app["name"]
                        for exe_name, config_name in app_mapping.items():
                            if config_name.lower() == app_name.lower():
                                app_to_level[f"Auto_{exe_name}"] = level_name
                                break
                logger.info(f"Loaded {len(app_to_level)} policy mappings")
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
                "@{Name='Bytes';Expression={(Get-Counter \"\\Network Interface(*)\\Bytes Total/sec\" -ErrorAction SilentlyContinue).CounterSamples.CookedValue}} | ConvertTo-Json"
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                check=True
            )
            logger.debug(f"Raw QoS output: {result.stdout}")
            return self._parse_qos_output(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get QoS stats: {e.stderr}")
            return {}

    def _parse_qos_output(self, output: str) -> Dict:
        """Parse PowerShell QoS output."""
        stats = {}
        try:
            qos_data = json.loads(output)
            if isinstance(qos_data, dict):
                qos_data = [qos_data]

            for policy in qos_data:
                policy_name = policy["Name"]
                level_name = self.priority_config.get(policy_name)
                if not level_name:
                    logger.debug(f"No priority level for policy: {policy_name}")
                    continue
                if level_name not in stats:
                    stats[level_name] = {"bytes": 0, "bandwidth": 0}
                stats[level_name]["bytes"] += int(policy.get("Bytes", 0) or 0)
                throttle_rate = policy.get("ThrottleRateActionBitsPerSecond")
                stats[level_name]["bandwidth"] = (throttle_rate / 1_000_000) if throttle_rate is not None else 0
            logger.info(f"Parsed {len(stats)} priority levels from QoS data")
        except json.JSONDecodeError:
            logger.error("Failed to parse QoS statistics")
        return stats

    def get_interface_stats(self) -> Dict:
        """Get interface statistics using PowerShell."""
        try:
            ps_command = (
                f"Get-NetAdapterStatistics -Name \"{self.interface}\" | "
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
            logger.error(f"Failed to get interface stats for {self.interface}: {e.stderr}")
            return {"input_bytes": 0, "output_bytes": 0}

    def _parse_interface_output(self, output: str) -> Dict:
        """Parse PowerShell interface statistics output."""
        stats = {"input_bytes": 0, "output_bytes": 0}
        try:
            data = json.loads(output)
            stats["input_bytes"] = data.get("ReceivedBytes", 0)
            stats["output_bytes"] = data.get("SentBytes", 0)
        except json.JSONDecodeError:
            logger.error("Failed to parse interface statistics")
        return stats

    def monitor(self, duration: int = 60) -> None:
        """Monitor traffic for the specified duration."""
        logger.info(f"Starting traffic monitoring for {duration} seconds on interface {self.interface}...")

        start_time = time.time()
        while time.time() - start_time < duration:
            try:
                qos_stats = self.get_qos_stats()
                interface_stats = self.get_interface_stats()

                print("\nTraffic Statistics:")
                print("------------------")
                if qos_stats:
                    for level_name, data in qos_stats.items():
                        bandwidth_label = f"{data['bandwidth']} MB/s" if data['bandwidth'] > 0 else "None (DSCP only)"
                        print(f"\n{level_name} Priority (Bandwidth Limit: {bandwidth_label})")
                        print(f"  Bytes: {data['bytes']}")
                else:
                    print("No QoS policies found. Ensure vpn_qos.py or vpn_gui.py has been run.")

                print("\nInterface Statistics:")
                print(f"  Input Bytes: {interface_stats.get('input_bytes', 0)}")
                print(f"  Output Bytes: {interface_stats.get('output_bytes', 0)}")

                total_bytes = sum(level["bytes"] for level in qos_stats.values())
                if total_bytes > 0:
                    print("\nBandwidth Allocation:")
                    for level_name, level_stats in qos_stats.items():
                        percent = (level_stats["bytes"] / total_bytes * 100)
                        print(f"  {level_name}: {percent:.2f}% (Target: {level_stats['bandwidth']} MB/s)")

                time.sleep(self.sample_interval)
            except Exception as e:
                logger.error(f"Error during monitoring: {str(e)}")
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