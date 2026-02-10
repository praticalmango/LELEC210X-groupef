import numpy as np

class ReceiverSim:
    def __init__(self, oversampling_rate, bit_rate):
        self.osr_rx = oversampling_rate
        self.bit_rate = bit_rate

    def cfo_estimation(self, y):
        """Your exact function provided in the prompt."""
        # Extract 2 blocks of size N*R at the start of y
        N = 8  # Number of bits per block
        R = self.osr_rx  # Receiver oversampling factor
        block_size = N * R  # Number of samples per block
        
        # Check if we have enough samples
        if len(y) < 2 * block_size:
            raise ValueError(f"Not enough samples. Need {2 * block_size}, got {len(y)}")
        
        # Extract the two consecutive blocks
        y1 = y[:block_size]  # First block
        y2 = y[block_size:2 * block_size]  # Second block
        
        # Apply the Moose algorithm
        correlation_sum = np.sum(y2 * np.conj(y1))
        angle = np.angle(correlation_sum)
        
        # Calculate the CFO estimate
        T = 1.0 / self.bit_rate  # Symbol period
        denominator = 2 * np.pi * (block_size * T / R)
        
        cfo_est = angle / denominator
        return cfo_est

# --- 1. Simulation Setup ---
BIT_RATE = 1000      # 1 kHz bit rate
OSR = 4              # Oversampling rate (4 samples per bit)
ACTUAL_CFO = 25.0    # We will introduce a 25 Hz error
NOISE_LEVEL = 0.1    # Small amount of noise

# --- 2. Generate the Preamble (The "Transmitter") ---
# The pattern: 1, 0, 1, 1, 0, 0, 1, 0
# bits_block = np.array([1, 0, 1, 1, 0, 0, 1, 0])
bits_block = np.array([0, 0, 0, 0, 0, 0, 0, 0])
# Repeat it twice (Block 1 + Block 2)
preamble_bits = np.concatenate([bits_block, bits_block])

# Modulate BPSK: 0 -> -1, 1 -> +1
symbols = 2 * preamble_bits - 1 

# Upsample (repeat each symbol R times)
tx_signal = np.repeat(symbols, OSR)

# --- 3. Apply Distortions (The "Channel") ---
# Create a time vector for the signal duration
t = np.arange(len(tx_signal)) / (BIT_RATE * OSR)

# Apply Frequency Offset: Multiply by e^(j * 2pi * f * t)
phase_rotation = np.exp(1j * 2 * np.pi * ACTUAL_CFO * t)
rx_signal = tx_signal * phase_rotation

print(f"rx signal (first 10 samples): {rx_signal[:30]}")
print(f"tx signal (first 10 samples): {tx_signal[:30]}")
# Add some random noise
noise = NOISE_LEVEL * (np.random.randn(len(rx_signal)) + 1j * np.random.randn(len(rx_signal)))
rx_signal_noisy = rx_signal + noise

# --- 4. Run Estimation (The "Receiver") ---
receiver = ReceiverSim(oversampling_rate=OSR, bit_rate=BIT_RATE)
estimated_cfo = receiver.cfo_estimation(rx_signal_noisy)

# --- 5. Results ---
print(f"Actual CFO Injected: {ACTUAL_CFO:.4f} Hz")
print(f"Estimated CFO:       {estimated_cfo:.4f} Hz")
print(f"Error:               {abs(ACTUAL_CFO - estimated_cfo):.4f} Hz")