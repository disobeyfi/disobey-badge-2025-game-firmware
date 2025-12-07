import random


def simple_hash(mac_int, prime=31):
    """A simple hash function for better distribution."""
    return (mac_int * prime) & 0xFFFFFFFFFFFF  # Ensure the result fits into 48 bits


def can_connect(mac1_int, mac2_int, spread_factor):
    """
    Checks if two MAC addresses can connect, considering the ESP32 manufacturer prefix.
    """
    # ESP32 MAC addresses typically start with 18:FE:34 (or variations)
    esp32_prefix = 0x18FE34  # Example prefix for ESP32 MAC addresses

    # Extract the prefix from the MAC address integers
    mac1_prefix = mac1_int >> 24  # Isolate the first 3 bytes.
    mac2_prefix = mac2_int >> 24

    # Early check: Ensure both MAC addresses start with the ESP32 prefix
    if mac1_prefix != esp32_prefix or mac2_prefix != esp32_prefix:
        return False

    # Apply simple hash function to mac addresses
    hashed_mac1 = simple_hash(mac1_int)
    hashed_mac2 = simple_hash(mac2_int)

    # Apply the spread factor logic
    group1 = (hashed_mac1 % spread_factor + mac1_int % spread_factor) % spread_factor
    group2 = (hashed_mac2 % spread_factor + mac2_int % spread_factor) % spread_factor

    return group1 == group2


def process_broadcast(broadcasting_mac, receiving_mac, spread_factor):
    """Processes a broadcast, handling MAC address format and connection logic."""
    try:
        mac1_int = int.from_bytes(broadcasting_mac, 'big') if isinstance(broadcasting_mac, bytes) else int(
            broadcasting_mac, 16)
        mac2_int = int.from_bytes(receiving_mac, 'big') if isinstance(receiving_mac, bytes) else int(receiving_mac, 16)
    except (ValueError, TypeError):
        return False
    return can_connect(mac1_int, mac2_int, spread_factor)


def generate_esp32_mac():
    """Generates a MAC address with the ESP32 prefix."""
    prefix = "18FE34"
    suffix = ''.join(random.choices('0123456789ABCDEF', k=6))
    mac = prefix + suffix
    return bytes.fromhex(mac)

def calculate_connectivity_statistics(macs, spread_factor):
    """Calculates connectivity statistics for a list of MAC addresses."""
    connections = []

    for receiving_mac in macs:
        matches_found = 0
        for broadcasting_mac in macs:
            if process_broadcast(broadcasting_mac, receiving_mac, spread_factor):
                matches_found += 1
        connections.append(matches_found)

    total_macs = len(connections)
    total_connections = sum(connections)
    avg_connections = total_connections / total_macs if total_macs > 0 else 0
    min_connections = min(connections) if connections else 0
    max_connections = max(connections) if connections else 0

    return avg_connections, min_connections, max_connections

def main():
    spread_factor = 180  # Adjust as needed for better distribution and connectivity

    # Generate example ESP32 MAC addresses
    macs = [generate_esp32_mac() for _ in range(1500)]

    average, minimum, maximum = calculate_connectivity_statistics(macs, spread_factor)
    print(f"Average connections: {average}")
    print(f"Minimum connections: {minimum}")
    print(f"Maximum connections: {maximum}")


    # Simulate broadcasts and connections
#    matches_per_mac = {}

#    for receiving_mac in macs:
#        matches_found = 0
#        for broadcasting_mac in macs:
#            if process_broadcast(broadcasting_mac, receiving_mac, spread_factor):
#                matches_found += 1
#        matches_per_mac[receiving_mac.hex()] = matches_found

#    # Print summary
#    no_matches_count = sum(1 for v in matches_per_mac.values() if v == 0)
#    print(f"Number of MACs with no matches: {no_matches_count}")
#    print(f"Total unique MACs: {len(matches_per_mac)}")



if __name__ == "__main__":
    main()
