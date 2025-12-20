import re
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def parse_measurement_file(filepath):
    """
    Parses the measurement text file with blocks like:
    CFO=...,STO=...
    EsN0dB=...
    packet_number=...,correct=...,payload=[...]
    """
    data = []
    current_entry = {}
    
    # We'll determine the expected payload pattern from the first correct packet
    expected_payload = None

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            
            if line.startswith("CFO="):
                # Start of a new packet block. If we have a previous one, save it.
                if current_entry:
                    data.append(current_entry)
                current_entry = {}
                
                # Parse CFO and STO
                # Format: CFO=7302.15...,STO=5
                m = re.search(r"CFO=([-\d\.]+),STO=([-\d\.]+)", line)
                if m:
                    current_entry['cfo'] = float(m.group(1))
                    current_entry['sto'] = float(m.group(2))
            
            elif line.startswith("EsN0dB="):
                # Parse SNR
                # Format: EsN0dB=40.06,GRXdB=20,...
                m = re.search(r"EsN0dB=([-\d\.]+)", line)
                if m:
                    current_entry['esn0'] = float(m.group(1))
            
            elif line.startswith("packet_number="):
                # Parse Packet Info
                # Format: packet_number=1,correct=True,payload=[0,1,...]
                m = re.search(r"packet_number=(\d+),correct=(True|False),payload=\[(.*?)\]", line)
                if m:
                    current_entry['pkt_num'] = int(m.group(1))
                    is_correct = (m.group(2) == 'True')
                    current_entry['correct'] = is_correct
                    
                    # Parse payload list
                    payload_str = m.group(3)
                    if payload_str:
                        payload = np.array([int(x) for x in payload_str.split(',')])
                    else:
                        payload = np.array([])
                    current_entry['payload'] = payload

                    # Define expected payload based on the first correct packet we see
                    if is_correct and expected_payload is None:
                        expected_payload = payload

        # Don't forget the last entry
        if current_entry:
            data.append(current_entry)

    return data, expected_payload

def compute_measurement_metrics(data, expected_payload):
    """
    Aggregates raw measurement packets into metrics (BER, PER, etc.)
    grouped by SNR.
    """
    if not data:
        return {}, [], []

    # If we never found a correct packet, assume a default range 0..99 or take the first one
    if expected_payload is None and len(data) > 0:
        expected_payload = np.arange(len(data[0].get('payload', [])))

    # Group data by rounded SNR (to 0.5 dB)
    grouped_data = {}
    
    # Track sequence numbers to detect missed packets (Preamble Mis-detection proxy)
    # Note: This requires the log to be somewhat sequential.
    
    for entry in data:
        # Binning SNR
        snr = round(entry.get('esn0', 0) * 2) / 2.0
        
        if snr not in grouped_data:
            grouped_data[snr] = {
                'bit_errors': 0,
                'total_bits': 0,
                'pkt_errors': 0,
                'total_pkts': 0,
                'cfo_values': [],
                'sto_values': [],
                'pkt_nums': []
            }
        
        group = grouped_data[snr]
        group['total_pkts'] += 1
        group['cfo_values'].append(entry.get('cfo', 0))
        group['sto_values'].append(entry.get('sto', 0))
        group['pkt_nums'].append(entry.get('pkt_num', 0))
        
        # PER
        if not entry.get('correct', False):
            group['pkt_errors'] += 1
        
        # BER
        # Calculate bit errors
        received_payload = entry.get('payload', np.array([]))
        
        # Ensure lengths match before comparing
        L = min(len(received_payload), len(expected_payload))
        
        if L > 0:
            # XOR comparison equivalent
            errors = np.sum(received_payload[:L] != expected_payload[:L])
            # Add difference in length as errors (optional, depends on definition)
            errors += abs(len(received_payload) - len(expected_payload))
            
            group['bit_errors'] += errors
            group['total_bits'] += len(expected_payload)

    # Calculate final metrics per SNR
    snrs = sorted(grouped_data.keys())
    metrics = {
        'BER': [], 'PER': [], 'RMSE_cfo': [], 'RMSE_sto': []
    }

    for snr in snrs:
        g = grouped_data[snr]
        
        metrics['BER'].append(g['bit_errors'] / max(1, g['total_bits']))
        metrics['PER'].append(g['pkt_errors'] / max(1, g['total_pkts']))
        
        # For RMSE, since we don't have the ground truth "tx_cfo", 
        # we calculate the Standard Deviation (jitter) of the measurements.
        # If the ground truth is 0, then RMSE = sqrt(mean(x^2)).
        # Here we use std dev as a proxy for stability.
        metrics['RMSE_cfo'].append(np.std(g['cfo_values']))
        metrics['RMSE_sto'].append(np.std(g['sto_values']))
        
    return metrics, snrs

def main():
    # --- Configuration ---
    sim_file = "sim_outputs3.csv"
    meas_file = "measurements3.txt"
    
    # --- 1. Load Simulation Data ---
    try:
        # Columns: EsN0, BER, PER, RMSE_cfo, RMSE_sto, Preamble_mis, Preamble_false
        sim_data = np.loadtxt(sim_file, delimiter="\t")
        
        # Handle case where file has only 1 row (1D array)
        if sim_data.ndim == 1:
            sim_data = sim_data.reshape(1, -1)
            
        sim_snr = sim_data[:, 0]
        sim_ber = sim_data[:, 1]
        sim_per = sim_data[:, 2]
        sim_rmse_cfo = sim_data[:, 3]
        sim_rmse_sto = sim_data[:, 4]
    except Exception as e:
        print(f"Error loading simulation file '{sim_file}': {e}")
        return

    # --- 2. Load and Process Measurement Data ---
    meas_metrics = None
    meas_snr = []
    
    if Path(meas_file).exists():
        raw_data, expected_payload = parse_measurement_file(meas_file)
        meas_metrics, meas_snr = compute_measurement_metrics(raw_data, expected_payload)
        print(f"Loaded {len(raw_data)} packets from {meas_file}")
    else:
        print(f"Warning: Measurement file '{meas_file}' not found.")

    # --- 3. Plotting ---
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle(f"Simulation vs Measurements Comparison")

    # BER Plot
    ax = axes[0, 0]
    ax.semilogy(sim_snr, sim_ber, '-s', label='Simulation')
    if meas_metrics:
        ax.semilogy(meas_snr, meas_metrics['BER'], 'x--', color='tab:orange', label='Measurement')
    ax.set_title("Bit Error Rate (BER)")
    ax.set_xlabel("Es/N0 [dB]")
    ax.set_ylabel("BER")
    ax.grid(True, which="both", ls="-")
    ax.legend()

    # PER Plot
    ax = axes[0, 1]
    ax.semilogy(sim_snr, sim_per, '-s', label='Simulation')
    if meas_metrics:
        ax.semilogy(meas_snr, meas_metrics['PER'], 'x--', color='tab:orange', label='Measurement')
    ax.set_title("Packet Error Rate (PER)")
    ax.set_xlabel("Es/N0 [dB]")
    ax.set_ylabel("PER")
    ax.grid(True, which="both", ls="-")
    ax.legend()

    # RMSE CFO Plot
    ax = axes[1, 0]
    ax.plot(sim_snr, sim_rmse_cfo, '-s', label='Simulation (RMSE)')
    if meas_metrics:
        # Note: Plotting Standard Deviation for measurements
        ax.plot(meas_snr, meas_metrics['RMSE_cfo'], 'x--', color='tab:orange', label='Measurement (Std Dev)')
    ax.set_title("CFO Stability (RMSE / Std Dev)")
    ax.set_xlabel("Es/N0 [dB]")
    ax.set_ylabel("Frequency Error")
    ax.grid(True)
    ax.legend()

    # RMSE STO Plot
    ax = axes[1, 1]
    ax.plot(sim_snr, sim_rmse_sto, '-s', label='Simulation (RMSE)')
    if meas_metrics:
        ax.plot(meas_snr, meas_metrics['RMSE_sto'], 'x--', color='tab:orange', label='Measurement (Std Dev)')
    ax.set_title("STO Stability (RMSE / Std Dev)")
    ax.set_xlabel("Es/N0 [dB]")
    ax.set_ylabel("Timing Error")
    ax.grid(True)
    ax.legend()

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()