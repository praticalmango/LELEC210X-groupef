import numpy as np
from scipy import signal
import matplotlib.pyplot as plt

# --- 1. Provided Coefficients (Original Filter) ---
FPGA_FIR_TAPS = np.array([
    -0.001201261290430126, 0.0020488944185569607, -0.0020751053507837938,
    4.910806933254215e-18, 0.004754535968663148, -0.00987450755161552,
    0.00995675888032359, -1.4391882903962387e-17, -0.018922538981281996,
    0.036214375130954504, -0.03468641976116993, 2.4803862788187382e-17,
    0.06848299151299582, -0.15293237705130486, 0.22297239138994396,
    0.7505245253702963, 0.22297239138994396, -0.15293237705130486,
    0.06848299151299582, 2.4803862788187385e-17, -0.034686419761169936,
    0.036214375130954504, -0.018922538981282003, -1.4391882903962393e-17,
    0.00995675888032359, -0.009874507551615532, 0.004754535968663151,
    4.910806933254215e-18, -0.0020751053507837946, 0.0020488944185569607,
    -0.001201261290430126
])

# --- 2. Design the New Filter ---
# We use normalized frequency where 1.0 represents the Nyquist frequency (Fs/2).
# (Note: If you know your Fs, e.g., Fs = 30.72e6, set nyq = Fs/2 and cutoff to real Hz)
num_taps = len(FPGA_FIR_TAPS) # Keep the same number of taps (31) for FPGA hardware constraints
normalized_cutoff = 0.48      # Example lower cutoff (adjust this value as needed)

# Generate new coefficients using a Hamming window
new_taps = signal.firwin(num_taps, normalized_cutoff, window='hamming')

print(f"new taps: {new_taps}")

# --- 3. Calculate Frequency Responses ---
# freqz returns frequencies (w) and complex frequency response (h)
w, h_orig = signal.freqz(FPGA_FIR_TAPS, worN=8000)
w, h_new = signal.freqz(new_taps, worN=8000)

# Convert x-axis to normalized frequency (0 to 1.0 where 1.0 is Nyquist)
freq_axis = w / np.pi 

# Calculate Magnitude in dB (using np.maximum to avoid log10(0) warnings in deep nulls)
mag_orig = 20 * np.log10(np.maximum(np.abs(h_orig), 1e-10))
mag_new = 20 * np.log10(np.maximum(np.abs(h_new), 1e-10))

# Calculate Phase in radians
phase_orig = np.unwrap(np.angle(h_orig))
phase_new = np.unwrap(np.angle(h_new))

# --- 4. Plot the Bode Diagram ---
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

# Plot Magnitude
ax1.plot(freq_axis, mag_orig, label='Original Coefficients', color='blue')
ax1.plot(freq_axis, mag_new, label=f'New Filter (Cutoff={normalized_cutoff})', color='red', linestyle='--')
ax1.set_title('Bode Diagram: Magnitude Response')
ax1.set_ylabel('Magnitude [dB]')
ax1.set_xlabel('Normalized Frequency (×π rad/sample)')
ax1.grid(True)
ax1.legend()

# Plot Phase
ax2.plot(freq_axis, phase_orig, label='Original Coefficients', color='blue')
ax2.plot(freq_axis, phase_new, label='New Filter', color='red', linestyle='--')
ax2.set_title('Bode Diagram: Phase Response')
ax2.set_ylabel('Phase [radians]')
ax2.set_xlabel('Normalized Frequency (×π rad/sample)')
ax2.grid(True)
ax2.legend()

plt.tight_layout()
plt.show()



# --- 5. Export for Quartus FIR Compiler II (Single Bank Fix) ---
output_filename = "limesdr_new_fir_coeffs.txt"

# Open the file and write all coefficients on ONE single line, separated by commas
with open(output_filename, "w") as f:
    # Convert each tap to a string with 10 decimal places, then join with commas
    f.write(", ".join([f"{tap:.10f}" for tap in new_taps]))

print(f"Successfully saved {len(new_taps)} coefficients as a single bank to {output_filename}")

