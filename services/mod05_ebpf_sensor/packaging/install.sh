#!/bin/bash
# packaging/install.sh
# LogRaven Standalone eBPF Sensor Systemd Installer

set -euo pipefail

echo "Installing LogRaven eBPF Runtime Sensor..."

INSTALL_DIR="/opt/lograven/sensor"
mkdir -p "${INSTALL_DIR}"

# Ensure BPF filesystem is mounted
if ! mountpoint -q /sys/fs/bpf; then
    mount -t bpf bpf /sys/fs/bpf
fi

cat << 'EOF' > /etc/systemd/system/lograven-ebpf-sensor.service
[Unit]
Description=LogRaven eBPF Runtime Reachability & Container Drift Sensor
After=network.target

[Service]
Type=simple
ExecStart=/opt/lograven/sensor/lograven-sensor-daemon
Restart=always
RestartSec=5
MemoryMax=64M
CPUQuota=15%
CapabilityBoundingSet=CAP_BPF CAP_PERFMON CAP_SYS_RESOURCE
AmbientCapabilities=CAP_BPF CAP_PERFMON CAP_SYS_RESOURCE

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo "LogRaven eBPF Sensor service installed successfully."
