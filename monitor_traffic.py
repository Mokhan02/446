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
        self.interface = self.detect_interface()
        self.sample_interval = 1
        self.dscp_to_tier = {
            46: "Ultra High",
            34: "High",
            28: "Medium",
            10: "Low"
        }

    def detect_interface(self) -> str:
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

    def get_qos_stats(self) -> Dict:
        try:
            ps_command = (
                "Get-NetQosPolicy | Select-Object Name, DSCPValue, "
                "@{Name='Bytes';Expression={(Get-Counter "
                "'\\Network Interface(*)\\Bytes Total/sec' -ErrorAction SilentlyContinue).CounterSamples.CookedValue}} "
                "| ConvertTo-Json"
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                check=True
            )
            return self._parse_qos_output(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get QoS stats: {e.stderr}")
            return {}

    def _parse_qos_output(self, output: str) -> Dict:
        stats = {}
        try:
            qos_data = json.loads(output)
            if isinstance(qos_data, dict):
                qos_data = [qos_data]

            for policy in qos_data:
                dscp = policy.get("DSCPValue")
                tier = self.dscp_to_tier.get(dscp, f"DSCP {dscp}")
                if tier not in stats:
                    stats[tier] = {"bytes": 0}
                stats[tier]["bytes"] += int(policy.get("Bytes", 0) or 0)
            logger.info(f"Parsed {len(stats)} tiers from DSCP mappings")
        except json.JSONDecodeError:
            logger.error("Failed to parse QoS statistics")
        return stats

    def get_interface_stats(self) -> Dict:
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
        stats = {"input_bytes": 0, "output_bytes": 0}
        try:
            data = json.loads(output)
            stats["input_bytes"] = data.get("ReceivedBytes", 0)
            stats["output_bytes"] = data.get("SentBytes", 0)
        except json.JSONDecodeError:
            logger.error("Failed to parse interface statistics")
        return stats

    def monitor(self, duration: int = 60) -> None:
        logger.info(f"Starting traffic monitoring for {duration} seconds on interface {self.interface}...")

        start_time = time.time()
        while time.time() - start_time < duration:
            try:
                qos_stats = self.get_qos_stats()
                interface_stats = self.get_interface_stats()

                print("\nTraffic Statistics:")
                print("------------------")
                for tier, data in qos_stats.items():
                    print(f"\n{tier} Priority (DSCP-mapped)")
                    print(f"  Bytes: {data['bytes']}")

                print("\nInterface Statistics:")
                print(f"  Input Bytes: {interface_stats['input_bytes']}")
                print(f"  Output Bytes: {interface_stats['output_bytes']}")

                total_bytes = sum(level["bytes"] for level in qos_stats.values())
                if total_bytes > 0:
                    print("\nBandwidth Allocation:")
                    for tier, level_stats in qos_stats.items():
                        percent = (level_stats["bytes"] / total_bytes * 100)
                        print(f"  {tier}: {percent:.2f}%")
                time.sleep(self.sample_interval)
            except Exception as e:
                logger.error(f"Error during monitoring: {e}")
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
