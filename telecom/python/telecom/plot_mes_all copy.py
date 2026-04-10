# from collections import defaultdict
# from pathlib import Path

# import matplotlib.pyplot as plt
# import numpy as np
# import pandas as pd


# def load_measurement_data(filepath, payload_len=100, esn0_tol=1.0, group_by_grx=False):
#     """Reads a .txt measurement file, removes outliers, and calculates average BER/PER and STO RMSE."""
#     expected_payload = np.arange(payload_len, dtype=np.uint8)
#     num_bits = payload_len * 8

#     data = defaultdict(list)
#     with open(filepath) as f:
#         for line in f.read().splitlines():
#             if line.startswith("CFO"):
#                 cfo, sto = line.split(",")
#                 data["cfo"].append(float(cfo.split("=")[1]))
#                 data["sto"].append(int(sto.split("=")[1]))
#             elif line.startswith("EsN0dB"):
#                 esn0, Grx, N0 = line.split(",")
#                 data["esn0"].append(float(esn0.split("=")[1]))
#                 data["Grx"].append(int(Grx.split("=")[1]))
#                 data["N0"].append(int(10 * np.log10(float(N0.split("=")[1]))))
#             elif line.startswith("packet"):
#                 *_, payload = line.split(",", maxsplit=2)
#                 payload = list(map(int, payload.split("=")[1][1:-1].split(",")))
#                 biterror = np.unpackbits(
#                     expected_payload ^ np.array(payload, dtype=np.uint8)
#                 ).sum()
#                 invalid = 1 if biterror > 0 else 0
#                 data["biterror"].append(biterror)
#                 data["invalid"].append(invalid)

#     df = pd.DataFrame.from_dict(data)
#     if df.empty:
#         return None

#     # Pre-calculate STO squared for RMSE computation later
#     df["sto_sq"] = df["sto"] ** 2

#     def remove_outliers(group):
#         median_esn0 = group["esn0"].median()
#         return group[
#             (group["esn0"] >= median_esn0 - esn0_tol)
#             & (group["esn0"] <= median_esn0 + esn0_tol)
#         ]

#     group_col = "Grx" if group_by_grx else "N0"
#     df = df.groupby(group_col, group_keys=False).apply(remove_outliers)

#     agg = (
#         df.groupby(group_col)
#         .agg(
#             esn0_mean=("esn0", "mean"),
#             per_mean=("invalid", "mean"),
#             biterror=("biterror", "sum"),
#             count=("biterror", "count"),
#             sto_sq_mean=("sto_sq", "mean"), # Mean of squared STO
#         )
#         .reset_index()
#     )

#     agg["ber_mean"] = agg["biterror"] / (agg["count"] * num_bits)
#     agg["rmse_sto"] = np.sqrt(agg["sto_sq_mean"]) # Root of the mean square
#     return agg


# def load_simulation_data(filepath):
#     """
#     Reads a .csv simulation file.
#     Expects columns: [EsN0s_dB, BER, PER, RMSE_cfo, RMSE_sto, preamble_mis, preamble_false]
#     """
#     data = np.loadtxt(filepath)
#     esn0_db = data[:, 0]
#     ber = data[:, 1]
#     per = data[:, 2]
#     rmse_sto = data[:, 4] # Extracting RMSE_sto from column index 4
#     return esn0_db, ber, per, rmse_sto


# def plot_results(measurement_files, simulation_files, payload_len=100, esn0_tol=1.0, group_by_grx=False):
#     """Generates BER, PER, and STO RMSE plots in three separate windows."""
    
#     # Create three separate figures and axes
#     fig_ber, ax_ber = plt.subplots(figsize=(7, 5))
#     fig_per, ax_per = plt.subplots(figsize=(7, 5))
#     fig_sto, ax_sto = plt.subplots(figsize=(7, 5))
    
#     # Set window titles
#     fig_ber.canvas.manager.set_window_title('BER Results')
#     fig_per.canvas.manager.set_window_title('PER Results')
#     fig_sto.canvas.manager.set_window_title('STO RMSE Results')

#     num_bits = payload_len * 8

#     # --- COLOR MATCHING LOGIC ---
#     # Extract base names to map matching simulations and measurements to the same color
#     base_names = set()
#     for f in simulation_files + measurement_files:
#         stem = Path(f).stem
#         base = stem.replace("sim_outputs_", "").replace("measurements_", "")
#         base_names.add(base)
        
#     color_palette = plt.rcParams['axes.prop_cycle'].by_key()['color']
#     # Map each unique base name to a color
#     color_map = {base: color_palette[i % len(color_palette)] for i, base in enumerate(sorted(base_names))}

#     # 1. Plot Simulation Data
#     for sim_file in simulation_files:
#         path = Path(sim_file)
#         if not path.exists():
#             print(f"Warning: Simulation file {sim_file} not found. Skipping.")
#             continue
            
#         esn0_db, sim_ber, sim_per, sim_rmse_sto = load_simulation_data(path)
#         base_name = path.stem.replace("sim_outputs_", "")
#         file_color = color_map.get(base_name, 'gray')
        
#         # Plot Theoretical Curve for BER/PER (Thicker, Black, High Z-order for visibility)
#         if sim_file == simulation_files[0]:
#             ber_th = 0.5 * np.exp(-(10 ** (esn0_db / 10.0)) / 2)
#             per_th = 1 - (1 - ber_th) ** num_bits
#             ax_ber.plot(esn0_db, ber_th, color='black', linestyle='-', linewidth=1.5, label="AWGN Th. FSK non-coh.", zorder=10)
#             ax_per.plot(esn0_db, per_th, color='black', linestyle='-', linewidth=1.5, label="AWGN Th. FSK non-coh.", zorder=10)
            
#         # Simulation lines are dotted (':')
#         ax_ber.plot(esn0_db, sim_ber, color=file_color, linestyle='--', linewidth=1, label=f"Sim: {path.stem}")
#         ax_per.plot(esn0_db, sim_per, color=file_color, linestyle='--', linewidth=1, label=f"Sim: {path.stem}")
#         ax_sto.plot(esn0_db, sim_rmse_sto, color=file_color, linestyle='--', linewidth=1, label=f"Sim: {path.stem}")

#     # 2. Plot Measurement Data
#     for meas_file in measurement_files:
#         path = Path(meas_file)
#         if not path.exists():
#             print(f"Warning: Measurement file {meas_file} not found. Skipping.")
#             continue
            
#         agg_data = load_measurement_data(path, payload_len, esn0_tol, group_by_grx)
#         if agg_data is not None:
#             base_name = path.stem.replace("measurements_", "")
#             file_color = color_map.get(base_name, 'gray')
            
#             # Measurement lines are plain solid with square markers ('-s')
#             ax_ber.plot(agg_data["esn0_mean"], agg_data["ber_mean"], color=file_color, linestyle='-', marker='s', label=f"Meas: {path.stem}")
#             ax_per.plot(agg_data["esn0_mean"], agg_data["per_mean"], color=file_color, linestyle='-', marker='s', label=f"Meas: {path.stem}")
#             ax_sto.plot(agg_data["esn0_mean"], agg_data["rmse_sto"], color=file_color, linestyle='-', marker='s', label=f"Meas: {path.stem}")

#     # 3. Apply Formatting to BER and PER
#     for ax, title, ylabel in zip([ax_ber, ax_per], 
#                                  ["Average Bit Error Rate", "Average Packet Error Rate"], 
#                                  ["BER", "PER"]):
#         ax.set_title(title)
#         ax.set_ylabel(ylabel)
#         ax.set_xlabel("$E_{s}/N_{0}$ [dB]")
#         ax.set_yscale("log")
#         ax.set_ylim((1e-5, 1))
#         ax.grid(True, which="major", ls="-", color='0.75')
#         ax.grid(True, which="minor", ls="--", color='0.85')
#         ax.legend()

#     # 4. Apply Formatting to STO RMSE
#     ax_sto.set_title("Symbol Timing Offset (STO) RMSE")
#     ax_sto.set_ylabel("RMSE STO (Samples)")
#     ax_sto.set_xlabel("$E_{s}/N_{0}$ [dB]")
#     ax_sto.grid(True, which="major", ls="-", color='0.75')
#     ax_sto.grid(True, which="minor", ls="--", color='0.85')
#     ax_sto.legend()

#     # Ensure everything fits nicely
#     fig_ber.tight_layout()
#     fig_per.tight_layout()
#     fig_sto.tight_layout()

#     # Opens all 3 windows simultaneously
#     plt.show()


# if __name__ == "__main__":
#     # ---------------------------------------------------------
#     # CONFIGURATION
#     # ---------------------------------------------------------
    
#     # 1. Define your measurement text files here
#     MEASUREMENT_FILES = [
#         "measurements_1_a.txt",
#         # "measurements_1_b.txt",
#         # "measurements_2_a.txt",
#         "measurements_3_a.txt",
#         "measurements_4_a.txt",
        
        
#     ]

#     # 2. Define your simulation csv files here
#     SIMULATION_FILES = [
#         "sim_outputs_1_a.csv",
#         "sim_outputs_3_a.csv",
#     ]

#     # 3. Global parameters
#     PAYLOAD_LENGTH = 100
#     ESN0_TOLERANCE = 1.0
#     GROUP_BY_GRX = False

#     # ---------------------------------------------------------
#     # EXECUTION
#     # ---------------------------------------------------------
    
#     plot_results(
#         measurement_files=MEASUREMENT_FILES, 
#         simulation_files=SIMULATION_FILES,
#         payload_len=PAYLOAD_LENGTH,
#         esn0_tol=ESN0_TOLERANCE,
#         group_by_grx=GROUP_BY_GRX
#     )



from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def load_measurement_data(filepath, payload_len=100, esn0_tol=1.0, group_by_grx=False):
    """Reads a .txt measurement file, removes outliers, and calculates average BER/PER and STO RMSE."""
    expected_payload = np.arange(payload_len, dtype=np.uint8)
    num_bits = payload_len * 8

    data = defaultdict(list)
    with open(filepath) as f:
        for line in f.read().splitlines():
            if line.startswith("CFO"):
                cfo, sto = line.split(",")
                data["cfo"].append(float(cfo.split("=")[1]))
                data["sto"].append(int(sto.split("=")[1]))
            elif line.startswith("EsN0dB"):
                esn0, Grx, N0 = line.split(",")
                data["esn0"].append(float(esn0.split("=")[1]))
                data["Grx"].append(int(Grx.split("=")[1]))
                data["N0"].append(int(10 * np.log10(float(N0.split("=")[1]))))
            elif line.startswith("packet"):
                *_, payload = line.split(",", maxsplit=2)
                payload = list(map(int, payload.split("=")[1][1:-1].split(",")))
                biterror = np.unpackbits(
                    expected_payload ^ np.array(payload, dtype=np.uint8)
                ).sum()
                invalid = 1 if biterror > 0 else 0
                data["biterror"].append(biterror)
                data["invalid"].append(invalid)

    df = pd.DataFrame.from_dict(data)
    if df.empty:
        return None

    # Pre-calculate STO squared for RMSE computation later
    df["sto_sq"] = df["sto"] ** 2

    def remove_outliers(group):
        median_esn0 = group["esn0"].median()
        return group[
            (group["esn0"] >= median_esn0 - esn0_tol)
            & (group["esn0"] <= median_esn0 + esn0_tol)
        ]

    group_col = "Grx" if group_by_grx else "N0"
    df = df.groupby(group_col, group_keys=False).apply(remove_outliers)

    agg = (
        df.groupby(group_col)
        .agg(
            esn0_mean=("esn0", "mean"),
            per_mean=("invalid", "mean"),
            biterror=("biterror", "sum"),
            count=("biterror", "count"),
            sto_sq_mean=("sto_sq", "mean"), # Mean of squared STO
        )
        .reset_index()
    )

    agg["ber_mean"] = agg["biterror"] / (agg["count"] * num_bits)
    agg["rmse_sto"] = np.sqrt(agg["sto_sq_mean"]) # Root of the mean square
    return agg


def load_simulation_data(filepath):
    """
    Reads a .csv simulation file.
    Expects columns: [EsN0s_dB, BER, PER, RMSE_cfo, RMSE_sto, preamble_mis, preamble_false]
    """
    data = np.loadtxt(filepath)
    esn0_db = data[:, 0]
    ber = data[:, 1]
    per = data[:, 2]
    rmse_sto = data[:, 4] # Extracting RMSE_sto from column index 4
    return esn0_db, ber, per, rmse_sto


def plot_results(measurement_files, simulation_files, payload_len=100, esn0_tol=1.0, group_by_grx=False):
    """Generates BER, PER, and STO RMSE plots in three separate windows."""
    
    # Create three separate figures and axes
    fig_ber, ax_ber = plt.subplots(figsize=(7, 5))
    fig_per, ax_per = plt.subplots(figsize=(7, 5))
    fig_sto, ax_sto = plt.subplots(figsize=(7, 5))
    
    # Set window titles
    fig_ber.canvas.manager.set_window_title('BER Results')
    fig_per.canvas.manager.set_window_title('PER Results')
    fig_sto.canvas.manager.set_window_title('STO RMSE Results')

    num_bits = payload_len * 8

    # --- COLOR MATCHING LOGIC ---
    # Extract unique custom labels provided in the dictionaries to map colors correctly
    unique_labels = []
    for label in list(measurement_files.values()) + list(simulation_files.values()):
        if label not in unique_labels:
            unique_labels.append(label)
        
    color_palette = plt.rcParams['axes.prop_cycle'].by_key()['color']
    # Map each unique custom label to a color
    color_map = {label: color_palette[i % len(color_palette)] for i, label in enumerate(unique_labels)}

    # 1. Plot Simulation Data
    sim_keys = list(simulation_files.keys())
    for sim_file, custom_label in simulation_files.items():
        path = Path(sim_file)
        if not path.exists():
            print(f"Warning: Simulation file {sim_file} not found. Skipping.")
            continue
            
        esn0_db, sim_ber, sim_per, sim_rmse_sto = load_simulation_data(path)
        file_color = color_map.get(custom_label, 'gray')
        
        # Plot Theoretical Curve for BER/PER (Thicker, Black, High Z-order for visibility)
        if sim_keys and sim_file == sim_keys[0]:
            ber_th = 0.5 * np.exp(-(10 ** (esn0_db / 10.0)) / 2)
            per_th = 1 - (1 - ber_th) ** num_bits
            ax_ber.plot(esn0_db, ber_th, color='black', linestyle='-', linewidth=1.5, label="AWGN Th. FSK non-coh.", zorder=10)
            ax_per.plot(esn0_db, per_th, color='black', linestyle='-', linewidth=1.5, label="AWGN Th. FSK non-coh.", zorder=10)
            
        # Simulation lines are dashed ('--')
        ax_ber.plot(esn0_db, sim_ber, color=file_color, linestyle='--', linewidth=1.5, label=f"Sim: {custom_label}")
        ax_per.plot(esn0_db, sim_per, color=file_color, linestyle='--', linewidth=1.5, label=f"Sim: {custom_label}")
        ax_sto.plot(esn0_db, sim_rmse_sto, color=file_color, linestyle='--', linewidth=1.5, label=f"Sim: {custom_label}")

    # 2. Plot Measurement Data
    for meas_file, custom_label in measurement_files.items():
        path = Path(meas_file)
        if not path.exists():
            print(f"Warning: Measurement file {meas_file} not found. Skipping.")
            continue
            
        agg_data = load_measurement_data(path, payload_len, esn0_tol, group_by_grx)
        if agg_data is not None:
            file_color = color_map.get(custom_label, 'gray')
            
            # Measurement lines are plain solid with square markers ('-s')
            ax_ber.plot(agg_data["esn0_mean"], agg_data["ber_mean"], color=file_color, linestyle='-', marker='s', label=f"Meas: {custom_label}")
            ax_per.plot(agg_data["esn0_mean"], agg_data["per_mean"], color=file_color, linestyle='-', marker='s', label=f"Meas: {custom_label}")
            ax_sto.plot(agg_data["esn0_mean"], agg_data["rmse_sto"], color=file_color, linestyle='-', marker='s', label=f"Meas: {custom_label}")

    # 3. Apply Formatting to BER and PER
    for ax, title, ylabel in zip([ax_ber, ax_per], 
                                 ["Average Bit Error Rate", "Average Packet Error Rate"], 
                                 ["BER", "PER"]):
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.set_xlabel("$E_{s}/N_{0}$ [dB]")
        ax.set_yscale("log")
        ax.set_ylim((1e-5, 1))
        ax.grid(True, which="major", ls="-", color='0.75')
        ax.grid(True, which="minor", ls="--", color='0.85')
        ax.legend()

    # 4. Apply Formatting to STO RMSE
    ax_sto.set_title("Symbol Timing Offset (STO) RMSE")
    ax_sto.set_ylabel("RMSE STO (Samples)")
    ax_sto.set_xlabel("$E_{s}/N_{0}$ [dB]")
    ax_sto.grid(True, which="major", ls="-", color='0.75')
    ax_sto.grid(True, which="minor", ls="--", color='0.85')
    ax_sto.legend()

    # Ensure everything fits nicely
    fig_ber.tight_layout()
    fig_per.tight_layout()
    fig_sto.tight_layout()

    # Opens all 3 windows simultaneously
    plt.show()


if __name__ == "__main__":
    # ---------------------------------------------------------
    # CONFIGURATION
    # ---------------------------------------------------------
    
    # 1. Define your measurement text files and their custom labels here
    # Format: { "filepath": "Custom Legend Label" }
    MEASUREMENT_FILES = {
        # "measurements_1_a.txt": "new STO est.",
        # "measurements_1_b.txt": "new STO est.",
        # "measurements_3_a.txt": "init STO est.",
        # "measurements_4_a.txt": "Config Type 4",
    }

    # 2. Define your simulation csv files and their custom labels here
    # If the label matches one in MEASUREMENT_FILES, they will automatically share a color!
    SIMULATION_FILES = {
        # "sim_outputs_1_a.csv": "new STO est.",
        # "sim_outputs_2_a.csv": "new STO est. 16",
        # "sim_outputs_3_a.csv": "init STO est.",
    }

    # 3. Global parameters
    PAYLOAD_LENGTH = 100
    ESN0_TOLERANCE = 1.0
    GROUP_BY_GRX = False

    # ---------------------------------------------------------
    # EXECUTION
    # ---------------------------------------------------------
    
    plot_results(
        measurement_files=MEASUREMENT_FILES, 
        simulation_files=SIMULATION_FILES,
        payload_len=PAYLOAD_LENGTH,
        esn0_tol=ESN0_TOLERANCE,
        group_by_grx=GROUP_BY_GRX
    )