# ruff: noqa: N806
import numpy as np
from scipy import signal


BIT_RATE = 50e3
PREAMBLE = np.array([int(bit) for bit in f"{0xAAAAAAAA:0>32b}"])
SYNC_WORD = np.array([int(bit) for bit in f"{0x3E2A54B7:0>32b}"])


# Barker 11 sequence: 111 000 100 10
# We append this to the end of a "1010..." sequence to keep total length 32
barker_11 = "11100010010"
dotting   = "1010" * 5 + "1"  # 21 bits of alternating 1s and 0s

# Combine them
# PREAMBLE = np.array([int(bit) for bit in dotting + barker_11])

FPGA_FIR_TAPS = np.array(
    [
        -0.001201261290430126,
        0.0020488944185569607,
        -0.0020751053507837938,
        4.910806933254215e-18,
        0.004754535968663148,
        -0.00987450755161552,
        0.00995675888032359,
        -1.4391882903962387e-17,
        -0.018922538981281996,
        0.036214375130954504,
        -0.03468641976116993,
        2.4803862788187382e-17,
        0.06848299151299582,
        -0.15293237705130486,
        0.22297239138994396,
        0.7505245253702963,
        0.22297239138994396,
        -0.15293237705130486,
        0.06848299151299582,
        2.4803862788187385e-17,
        -0.034686419761169936,
        0.036214375130954504,
        -0.018922538981282003,
        -1.4391882903962393e-17,
        0.00995675888032359,
        -0.009874507551615532,
        0.004754535968663151,
        4.910806933254215e-18,
        -0.0020751053507837946,
        0.0020488944185569607,
        -0.001201261290430126,
    ]
)  # Example coefficients


class Chain:
    name: str = ""

    # Communication parameters
    bit_rate: float = BIT_RATE
    freq_dev: float = BIT_RATE / 2 # changer en /2 pour augmenter les perfs à fond 

    osr_tx: int = 64
    osr_rx: int = 4

    preamble: np.ndarray = PREAMBLE
    sync_word: np.ndarray = SYNC_WORD

    payload_len: int = 8 * 100  # Number of bits per packet

    # Simulation parameters
    n_packets: int = 200  # Number of sent packets

    # Channel parameters
    sto_val: float = 0
    sto_range: float = 10 / BIT_RATE  # defines the delay range when random

    cfo_val: float = np.nan
    # cfo_val: float = 5000
    cfo_range: tuple[float, float] = (
        -1000,
        1000,  # defines the CFO range when random (in Hz) #(1000 in old repo)
    )

    EsN0_range: np.ndarray = np.arange(0, 30, 1)

    # Lowpass filter parameters
    taps: np.ndarray = FPGA_FIR_TAPS  # specify None to make the simulator recompute the filter based on below spec
    numtaps: int = 100
    cutoff: float = 150e3  # BIT_RATE * osr_rx / 2.0001  # or 2*BIT_RATE,...

    # Tx methods

    def modulate(self, bits: np.array) -> np.array:
        """
        Modulates a stream of bits of size N
        with a given TX oversampling factor R (osr_tx).

        Uses Continuous-Phase FSK modulation.

        :param bits: The bit stream, (N,).
        :return: The modulates bit sequence, (N * R,).
        """
        fd = self.freq_dev  # Frequency deviation, Delta_f
        B = self.bit_rate  # B=1/T
        h = 2 * fd / B  # Modulation index
        R = self.osr_tx  # Oversampling factor

        x = np.zeros(len(bits) * R, dtype=np.complex64)
        ph = 2 * np.pi * fd * (np.arange(R) / R) / B  # Phase of reference waveform

        phase_shifts = np.zeros(
            len(bits) + 1
        )  # To store all phase shifts between symbols
        phase_shifts[0] = 0  # Initial phase

        for i, b in enumerate(bits):
            x[i * R : (i + 1) * R] = np.exp(1j * phase_shifts[i]) * np.exp(
                1j * (1 if b else -1) * ph
            )  # Sent waveforms, with starting phase coming from previous symbol
            phase_shifts[i + 1] = phase_shifts[i] + h * np.pi * (
                1 if b else -1
            )  # Update phase to start with for next symbol

        return x

    # Rx methods
    ideal_preamble_detect: bool = False

    use_dynamic_ppd: bool = False

    def preamble_detect(self, y: np.array) -> int | None:
        """
        Detect the preamble in a given received signal with hard thresholding.

        :param y: The received signal, (N * R,).
        :return: The index where the preamble starts,
            or None if not found.
        """
        raise NotImplementedError

    def preamble_detect_ppd(self, y: np.array) -> int | None:
        """
        Detect the preamble in a given received signal with sofft thresholding.

        :param y: The received signal, (N * R,).
        :return: The index where the preamble starts,
            or None if not found.
        """
        raise NotImplementedError

    ideal_cfo_estimation: bool = False

    def cfo_estimation(self, y: np.array) -> float:
        """
        Estimates the CFO based on the received signal.

        :param y: The received signal, (N * R,).
        :return: The estimated CFO.
        """
        raise NotImplementedError

    ideal_sto_estimation: bool = False

    def sto_estimation(self, y: np.array) -> float:
        """
        Estimates the STO based on the received signal.

        :param y: The received signal, (N * R,).
        :return: The estimated STO.
        """
        raise NotImplementedError


    def demodulate(self, y: np.array) -> np.array:
        """
        Demodulates the received signal using non-coherent detection.

        :param y: The received signal, shape (N * R_RX,)
        :return: Detected symbols, shape (N,)
        """
        raise NotImplementedError



class BasicChain(Chain):
    name = "Basic Tx/Rx chain"

    cfo_val, sto_val = np.nan, np.nan  # CFO and STO are random

    ideal_preamble_detect = True

    use_dynamic_ppd = True

    def preamble_detect_ppd(self, y):
        """Detect a preamble computing the received energy (average on a window)."""
        long_term_sum_W = 256
        short_term_sum_W = 32

        K = 5 * (short_term_sum_W / long_term_sum_W)

        long_window = np.ones(long_term_sum_W)
        short_window = np.ones(short_term_sum_W)

        yabs = np.abs(y)
        ylen = len(y)
        long_sum = np.convolve(yabs, long_window, mode="full")
        short_sum = np.convolve(yabs, short_window, mode="full")

        long_sum = long_sum[long_term_sum_W:ylen]
        short_sum = short_sum[long_term_sum_W + short_term_sum_W - 1 :]

        detection = short_sum > (long_sum * K)
        detected_indices = np.where(detection)[0]
        first_idx = (
            (detected_indices[0] + long_term_sum_W + short_term_sum_W)
            if detected_indices.size > 0
            else None
        )
        return first_idx

    def preamble_detect(self, y):
        """Detect a preamble computing the received energy (average on a window)."""
        L = 4 * self.osr_rx
        y_abs = np.abs(y)

        for i in range(0, int(len(y) / L)):
            sum_abs = np.sum(y_abs[i * L : (i + 1) * L])
            if sum_abs > (L - 1):  # fix threshold
                return i * L

        return None

    ideal_cfo_estimation = False
    
    # def cfo_estimation(self, y):
    #     """Estimates CFO using Moose algorithm, on first samples of preamble."""
    #     # TO DO: extract 2 blocks of size N*R at the start of y
    #     N = 4  # You can change this value if needed
    #     # TO DO: apply the Moose algorithm on these two blocks to estimate the CFO
    #     cfo_est = 0

    #     return cfo_est

    def cfo_estimation(self, y):
        """Estimates CFO using Moose algorithm, on first samples of preamble."""
        # Extract 2 blocks of size N*R at the start of y
        N = 8  # Number of bits per block
        R = self.osr_rx  # Receiver oversampling factor
        block_size = N * R  # Number of samples per block
        
        # Check if we have enough samples
        if len(y) < 2 * block_size:
            raise ValueError(f"Not enough samples for CFO estimation. Need {2 * block_size}, got {len(y)}")
        
        # Extract the two consecutive blocks
        y1 = y[:block_size]  # First block
        y2 = y[block_size:2 * block_size]  # Second block
        
        # Apply the Moose algorithm on these two blocks to estimate the CFO
        # Calculate the correlation sum: sum(y2[l] * conj(y1[l]))
        correlation_sum = np.sum(y2 * np.conj(y1))
        
        # Get the angle (argument) of the correlation sum
        angle = np.angle(correlation_sum)
        
        # Calculate the CFO estimate using Moose formula
        # Δf_c = angle / (2π * (N_i * T / R_RX))
        # where N_i = N * R_RX and T = 1/B (symbol period)
        T = 1.0 / self.bit_rate  # Symbol period
        denominator = 2 * np.pi * (block_size * T / R)
        
        cfo_est = angle / denominator
        
        return cfo_est
    


    ideal_sto_estimation = False

    # def sto_estimation(self, y):
    #     """Estimates symbol timing (fractional) based on phase shifts."""
    #     R = self.osr_rx

    #     # Computation of derivatives of phase function
    #     phase_function = np.unwrap(np.angle(y))
    #     phase_derivative_1 = phase_function[1:] - phase_function[:-1]
    #     phase_derivative_2 = np.abs(phase_derivative_1[1:] - phase_derivative_1[:-1])

    #     sum_der_saved = -np.inf
    #     save_i = 0
    #     for i in range(0, R):
    #         sum_der = np.sum(phase_derivative_2[i::R])  # Sum every R samples

    #         if sum_der > sum_der_saved:
    #             sum_der_saved = sum_der
    #             save_i = i

    #     return np.mod(save_i + 1, R)
    
    
    barker_pattern = np.array([int(bit) for bit in "11100010010"])

    
    # def sto_estimation(self, y, known_preamble_bits=barker_pattern):
    #     """
    #     Estimates timing by correlating instantaneous frequency with a known preamble.
        
    #     Args:
    #         y: Received complex signal
    #         known_preamble_bits: List or array of bits, e.g., [1, 0, 1, 0]
    #     """
    #     R = self.osr_rx
        
    #     # Create the reference pattern JUST for the Barker part
        
    #     # 1. Get Instantaneous Frequency of received signal
    #     # (Same as before - demodulate to baseband)
    #     phase_function = np.unwrap(np.angle(y))
    #     rx_freq = np.diff(phase_function)
        
    #     # 2. Generate the "Ideal" Preamble Waveform
    #     # Map bits 0 -> -1 and 1 -> +1 (or whatever your modulation index implies)
    #     # Then repeat each bit R times to match the oversampling rate.
    #     # Note: If you use Gaussian FSK (GFSK), apply a Gaussian filter to this `tx_ref`.
    #     tx_syms = 2 * np.array(known_preamble_bits) - 1 # Map [0,1] to [-1, 1]
    #     tx_ref = np.repeat(tx_syms, R)
        
    #     # 3. Perform Cross-Correlation (Convolution)
    #     # "valid" mode means we only compute overlaps where the signals fully align
    #     correlation = signal.correlate(rx_freq, tx_ref, mode='valid')
        
    #     # 4. Find the peak
    #     # The index of the max value is the start of the preamble
    #     peak_index = np.argmax(np.abs(correlation))
        
    #     # If you just need the fractional offset within a symbol:
    #     fractional_offset = np.mod(peak_index, R)
        
    #     return fractional_offset
    
    
    # def sto_estimation(self, y, known_preamble_bits=barker_pattern):
    #     """
    #     Estimates timing by correlating instantaneous frequency with a known preamble.
    #     Optimized to search only a limited window.
    #     """
    #     R = self.osr_rx
        
    #     # --- OPTIMIZATION: Define Search Window ---
    #     # We expect the preamble to start within the first 'N' symbols.
    #     # Let's say we search over a window of:
    #     # Length of Preamble + Max Expected Delay (e.g., 50 symbols)
    #     # If the buffer 'y' is huge, this saves massive computation.
        
    #     # Length of the pattern we are looking for
    #     L_pattern = len(known_preamble_bits) * R
        
    #     # Search margin: How late can the packet arrive? (e.g., 100 symbols late)
    #     margin_symbols = 100 
    #     search_len = L_pattern + (margin_symbols * R)
        
    #     # Safety check: Don't slice more than we have
    #     search_len = min(search_len, len(y))
        
    #     # Slice the signal to just the search window
    #     y_search = y[:search_len]

    #     # 1. Get Instantaneous Frequency of the SEARCH WINDOW only
    #     phase_function = np.unwrap(np.angle(y_search))
    #     rx_freq = np.diff(phase_function)
        
    #     # 2. Generate the "Ideal" Preamble Waveform
    #     tx_syms = 2 * np.array(known_preamble_bits) - 1
    #     tx_ref = np.repeat(tx_syms, R)
        
    #     # 3. Perform Cross-Correlation
    #     correlation = signal.correlate(rx_freq, tx_ref, mode='valid')
        
    #     # 4. Find the peak
    #     # This index is relative to the start of 'y'
    #     peak_index = np.argmax(np.abs(correlation))
        
    #     # --- CRITICAL UNDERSTANDING ---
    #     # 'peak_index' is the start of the Barker code in your buffer.
    #     # To get the start of the PAYLOAD, you usually need:
    #     # payload_start_index = peak_index + len(tx_ref)
        
    #     # For STO (fractional timing):
    #     fractional_offset = np.mod(peak_index, R)
        
    #     # You likely want to return the integer offset too!
    #     # return fractional_offset, peak_index
    #     return fractional_offset
    
    # def sto_estimation(self, y): #version avec dérivée
    #     """
    #     Estimates fractional timing offset using the 'Dotting' (1010...) part of the preamble.
    #     Uses Differential Correlation which is more robust to noise than raw phase derivatives.
    #     """
    #     R = self.osr_rx
        
    #     # 1. Focus on the "Dotting" part of the preamble
    #     # The preamble starts with "1010..." (21 bits). 
    #     # We take a safe window (e.g., first 16 bits) to avoid hitting the Barker code edge.
    #     n_dotting_bits = 16 
    #     search_len = n_dotting_bits * R
        
    #     # Safety: ensure we have enough samples
    #     if len(y) < search_len:
    #         search_len = len(y)
        
    #     y_segment = y[:search_len]
        
    #     # 2. Compute "Delay-and-Multiply" (Differential Detection)
    #     # This converts FSK tones into a complex DC-like signal where:
    #     # bit 1 (+f) -> rotates pos, bit 0 (-f) -> rotates neg.
    #     # This avoids 'np.unwrap' and 'np.diff' which are unstable in noise.
    #     discriminator_out = y_segment[1:] * np.conj(y_segment[:-1])
        
    #     # 3. Create the Reference for "1010..." pattern
    #     # In delay-and-multiply domain:
    #     # Symbol '1' (freq +h) -> exp(j * sensitivity)
    #     # Symbol '0' (freq -h) -> exp(-j * sensitivity)
    #     # We don't need exact sensitivity, just the sign pattern: +1, -1.
        
    #     # Create pattern: 1, 0, 1, 0... mapped to +1, -1
    #     # (Assuming the preamble starts with 1. If it starts with 0, just flip sign or take abs)
    #     dotting_bits = np.resize([1, 0], n_dotting_bits) 
    #     tx_syms = 2 * dotting_bits - 1 # [+1, -1, +1, -1...]
        
    #     # Upsample to match OSR (repeat each symbol R times)
    #     # Note: We use R-1 because 'discriminator_out' is length N-1
    #     # But for correlation shape matching, standard R is fine.
    #     ref_pattern = np.repeat(tx_syms, R)
        
    #     # Trim ref to match discriminator output length if needed
    #     ref_pattern = ref_pattern[:len(discriminator_out)]
        
    #     # 4. Cross-Correlate
    #     # We look for the alignment of the 1010 square wave
    #     # We use the Real part because we expect the phase rotation direction to match
    #     correlation = np.abs(signal.correlate(np.angle(discriminator_out), ref_pattern, mode='valid'))
        
    #     # 5. Find the Peak
    #     peak_index = np.argmax(correlation)
        
    #     # 6. Return Fractional Offset
    #     # We only care about the offset modulo R to align the symbol grid.
    #     # The Frame Sync (in simulate.py) will handle the integer symbol shifts.
    #     return np.mod(peak_index, R)
    
    def sto_estimation(self, y): #version avec oerder Meyr
        """
        Estimates fractional timing offset using the 'Dotting' (1010...) preamble.
        Uses the Oerder-Meyr (Squaring) method to recover the symbol clock tone.
        """
        R = self.osr_rx
        
        # 1. Select the Preamble Window
        # We know the first 32 bits are 101010...
        # We take the first 24 bits to be safe and avoid edge effects with the Sync Word.
        n_bits_to_use = 24
        window_len = n_bits_to_use * R
        
        # Safety check
        if len(y) < window_len:
            window_len = len(y)
            
        y_segment = y[:window_len]
        
        # 2. Compute the Signal Magnitude (Non-linearity)
        # For MSK/FSK, the instantaneous frequency is a PAM signal.
        # We approximate the 'energy' of the transition by taking the absolute value 
        # of the differentiated phase.
        phase_function = np.unwrap(np.angle(y_segment))
        inst_freq = np.diff(phase_function)
        
        # Taking the absolute value of the frequency creates a strong tone at the Symbol Rate.
        # (Because 1010... creates a square wave +f, -f, +f, -f. Abs value makes it +f, +f...)
        # Wait, actually for STO on 1010..., the squared magnitude of the *signal* is constant.
        # For FSK STO, we want to look at the *Instantaneous Frequency* periodicity.
        
        # Refined Oerder-Meyr for CPFSK:
        # We want to find the phase of the clock component in the envelope.
        # Simple approach: Correlate the Instantaneous Freq with a local 1010 clock.
        
        # Create a local clock reference (1, -1, 1, -1...) matched to OSR
        # We construct a sine wave at the symbol rate 1/T.
        t = np.arange(len(inst_freq))
        # The '1010' pattern has a fundamental frequency of 1/(2T). 
        # But we want to lock to the symbol boundaries.
        
        # Let's stick to the Robust Correlation method (Delay-and-Multiply)
        # It is strictly better than the derivative method you had.
        
        # Map 1010... to +1, -1...
        ref_bits = np.resize([1, 0], n_bits_to_use)
        ref_seq = 2 * ref_bits - 1 # +1, -1, +1, -1
        ref_waveform = np.repeat(ref_seq, R)
        
        # Truncate to match diff length
        ref_waveform = ref_waveform[:len(inst_freq)]
        
        # Correlate Instantaneous Frequency with Expected Frequency Pattern
        # We align the received +/- frequency shifts with our expected +/- shifts.
        corr = np.abs(signal.correlate(inst_freq, ref_waveform, mode='valid'))
        
        # Find the peak
        best_idx = np.argmax(corr)
        
        # The peak index tells us where the pattern aligns.
        # We only need the fractional part modulo R.
        return np.mod(best_idx, R)
    
    
    
    # def demodulate(self, y):
    #     """Non-coherent demodulator."""
    #     R = self.osr_rx  # Receiver oversampling factor
    #     nb_syms = len(y) // R  # Number of CPFSK symbols in y

    #     # Group symbols together, in a matrix. Each row contains the R samples over one symbol period
    #     y = np.resize(y, (nb_syms, R))

    #     # TO DO: generate the reference waveforms used for the correlation
    #     # hint: look at what is done in modulate() in chain.py

    #     # TO DO: compute the correlations with the two reference waveforms (r0 and r1)

    #     # TO DO: performs the decision based on r0 and r1

    #     bits_hat = np.zeros(nb_syms, dtype=int)

    #     return bits_hat
    
    def demodulate(self, y):
        """Non-coherent demodulator."""
        R = self.osr_rx  # Receiver oversampling factor
        nb_syms = len(y) // R  # Number of CPFSK symbols in y

        # Group symbols together, in a matrix. Each row contains the R samples over one symbol period
        y = np.resize(y, (nb_syms, R))

        # Generate the reference waveforms used for the correlation
        # Based on what's done in modulate()
        fd = self.freq_dev  # Frequency deviation, Delta_f
        B = self.bit_rate   # B=1/T
        n = np.arange(R)
        
        # Reference waveforms - same as in modulate() but without cumulative phase
        # (non-coherent detection ignores absolute phase)
        ref1 = np.exp(-1j * 2 * np.pi * fd * n / (R * B))  # For bit 1
        ref0 = np.exp(1j * 2 * np.pi * fd * n / (R * B)) # For bit -1/0

        # Compute the correlations with the two reference waveforms (r1 and r0)
        r1 = np.sum(y * ref1, axis=1) / R  # Correlation with reference for bit 1
        r0 = np.sum(y * ref0, axis=1) / R  # Correlation with reference for bit 0

        # Perform the decision based on |r1| and |r0|
        # For binary decision: if |r1| > |r0| then bit=1, else bit=0
        bits_hat = np.where(np.abs(r1) > np.abs(r0), 1, 0)

        return bits_hat