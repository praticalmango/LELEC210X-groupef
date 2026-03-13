import pandas as pd
import matplotlib.pyplot as plt

# 1. Load the data, skipping the first 7 rows of metadata
# df = pd.read_csv('mcu_aes_accel.csv', skiprows=7)
# df = pd.read_csv('mcu_aes_non_accel.csv', skiprows=7)
# df = pd.read_csv('mcu_32_non_accel.csv', skiprows=7)
df = pd.read_csv('mcu_32_accel.csv', skiprows=7)



# 2. Define the timeframe
# start_time = 0.114
# end_time = 1.308
# start_time = -0.754
# end_time = 0.528
# start_time = -0.804
# end_time = 1.044
start_time = -0.612
end_time = 1.108


# Filter the dataframe to only include data within the timeframe
df_filtered = df[(df['Time(S)'] >= start_time) & (df['Time(S)'] <= end_time)].copy()

# 3. Calculate Current (I = V_drop / R)
# The resistance is 47 Ohms
df_filtered['Current(A)'] = df_filtered['CH1(V)'] / 47.0

# 4. Calculate MCU Voltage (V_mcu = V_supply - V_drop)
# The supply voltage is 3.3V
# Power (W) = V_mcu * Current
df_filtered['Power(W)'] = 3.3 * df_filtered['Current(A)']

# Convert to milliwatts for a cleaner plot
df_filtered['Power(mW)'] = df_filtered['Power(W)'] * 1000.0


# ... (previous code filtering the dataframe and calculating power)

# Calculate the average power in milliwatts
energy = df_filtered['Power(mW)'].mean()*(df_filtered['Time(S)'].iloc[-1] - df_filtered['Time(S)'].iloc[0])

print(f"Average MCU Power ({start_time}s to {end_time}s): {df_filtered['Power(mW)'].mean():.2f} mW")
print(f"Total Energy Consumption: {energy:.2f} mJ")

# 5. Create the plot
plt.figure(figsize=(10, 6))
plt.plot(df_filtered['Time(S)'], df_filtered['Power(mW)'], label='MCU Power', color='b')

# 6. Format the plot
plt.xlabel('Time (s)')
plt.ylabel('Power (mW)')
plt.title(f'MCU Power Consumption')
plt.grid(True)
plt.legend()
plt.tight_layout()

# Show the plot
plt.show()