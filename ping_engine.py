import subprocess
import platform
import re

def ping_device(ip):
    system = platform.system()

    # Windows uses -n, Linux uses -c
    if system == "Windows":
        command = ["ping", "-n", "2", "-w", "100", ip]
    else:
        command = ["ping", "-c", "2", "-W", "1", ip]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,

        )

        output = result.stdout.decode('utf-8', errors='ignore')

        if result.returncode == 0:
            # Extract response time from ping output
            if system == "Windows":
                # Windows output: "Average = 23ms"
                match = re.search(r'Average = (\d+)ms', output)
            else:
                # Linux output: "rtt min/avg/max = 1.234/2.345/3.456 ms"
                match = re.search(r'rtt min/avg/max = [\d.]+/([\d.]+)/', output)

            if match:
                response_time = int(float(match.group(1)))
            else:
                response_time = 0

            return "UP", response_time
        else:
            return "DOWN", None

    except Exception as e:
        print(f"Error pinging {ip}: {e}")
        return "UNKNOWN", None


# ── Test it directly ──
if __name__ == "__main__":
    test_ips = [
        "8.8.8.8",
        "1.1.1.1",
        "192.168.1.1",
        "192.168.1.255",
        "10.0.0.99",
    ]

    print("Testing ping engine...\n")
    for ip in test_ips:
        status, response_time = ping_device(ip)
        symbol = "🟢" if status == "UP" else "🔴"
        if response_time is not None:
            print(f"  {symbol} {ip} → {status} ({response_time}ms)")
        else:
            print(f"  {symbol} {ip} → {status}")