import matplotlib.pyplot as plt
import numpy as np

# Data
# Parsing '1m50' as 1.5m and '2m50' as 2.5m
distances = np.array([1.0, 1.5, 2.0, 2.5, 3.0, 4.0])
en0_values = np.array([40.8, 36.5, 34.95, 34.49, 32.5, 18.0])

distances_bis = np.arange(1,50,0.1)


# Create the plot
plt.figure(figsize=(10, 6))

# Plot data points
plt.plot(distances, en0_values,"bo", label='Measured E/N0')

# Optional: Add a theoretical Free Space Path Loss (FSPL) reference line for comparison
# assuming it matches the first point (1m). slope -20dB/decade
# y = a - 20 * log10(x)
# ref_line = en0_values[0] - 20 * np.log10(distances)
ref_line = en0_values[0] - 20 * np.log10(distances_bis)

# plt.plot(distances, ref_line, linestyle='-', color='tab:red', alpha=0.7, label='Theoretical FSPL')
plt.plot(distances_bis, ref_line, linestyle='-', color='tab:red', alpha=0.7, label='Theoretical FSPL')

plt.title(r'$\frac{\epsilon}{N_0}$ vs Distance')
plt.xlabel('Distance [m]')
# plt.xlim(0, 4.5)
plt.ylabel(r'$\frac{\epsilon}{N_0}$ [dB]')
plt.grid(True, which='both', linestyle='--')
plt.legend()

# Show the plot
plt.show()