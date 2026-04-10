# ruff: noqa: N806
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt


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


FPGA_FIR_TAPS_1 = np.array([-0.001201261290430126, 0.0020488944185569607, -0.0020751053507837938, 4.910806933254215E-18, 0.004754535968663148, -0.00987450755161552, 0.00995675888032359, -1.4391882903962387E-17, -0.018922538981281996, 0.036214375130954504, -0.03468641976116993, 2.4803862788187382E-17, 0.06848299151299582, -0.15293237705130486, 0.22297239138994396, 0.7505245253702963, 0.22297239138994396, -0.15293237705130486, 0.06848299151299582, 2.4803862788187385E-17, -0.034686419761169936, 0.036214375130954504, -0.018922538981282003, -1.4391882903962393E-17, 0.00995675888032359, -0.009874507551615532, 0.004754535968663151, 4.910806933254215E-18, -0.0020751053507837946, 0.0020488944185569607, -0.001201261290430126])


FPGA_FIR_TAPS_2 = np.array(
    [-0.00099754,  0.0015771,   0.00200687, -0.00304694, -0.00517564,  0.00579822,
     0.01187695, -0.0094263,  -0.02418915,  0.01331792,  0.04660596, -0.01677282,
     -0.09503791,  0.01914813,  0.31439014,  0.47985002,  0.31439014,  0.01914813,
     -0.09503791, -0.01677282,  0.04660596,  0.01331792, -0.02418915, -0.0094263,
     0.01187695,  0.00579822, -0.00517564, -0.00304694,  0.00200687,  0.0015771,
     -0.00099754])



# --- Golay (24, 12) Implementation Details ---
GOLAY_P_HEX = [0x8ED, 0x476, 0x23B, 0x11D, 0x08E, 0x047, 
               0x823, 0x411, 0x208, 0x104, 0x082, 0x041]

def _generate_golay_utils():
    P = np.array([[(x >> i) & 1 for i in range(11, -1, -1)] for x in GOLAY_P_HEX])
    G = np.hstack((np.eye(12, dtype=int), P))
    H = np.hstack((P.T, np.eye(12, dtype=int)))
    
    # Fast Lookup Table for Error Correction (Up to 3 errors)
    syndromes = {}
    # Generate all error patterns with weight <= 3
    for i in range(25): # 0 to 24 errors
        indices = [()] if i == 0 else __import__('itertools').combinations(range(24), i)
        for idx in indices:
            if i > 3: break 
            e = np.zeros(24, dtype=int)
            if idx: e[list(idx)] = 1
            s = tuple((e @ H.T) % 2)
            if s not in syndromes: syndromes[s] = e
        if i == 3: break
    return G, H, syndromes

G_MAT, H_MAT, SYNDROME_TABLE = _generate_golay_utils()

class Chain:
    name: str = ""

    # Communication parameters
    bit_rate: float = BIT_RATE
    freq_dev: float = BIT_RATE / 2 # changer en /2 pour augmenter les perfs à fond 

    osr_tx: int = 64
    osr_rx: int = 8

    preamble: np.ndarray = PREAMBLE
    sync_word: np.ndarray = SYNC_WORD

    payload_len: int = 8 * 100 + 4  # Number of bits per packet

    # Simulation parameters
    n_packets: int = 500  # Number of sent packets

    # Channel parameters
    sto_val: float = np.nan
    sto_range: float = 10 / BIT_RATE  # defines the delay range when random

    cfo_val: float = np.nan
    # cfo_val: float = 5000
    cfo_range: tuple[float, float] = (
        -1000,
        1000,  # defines the CFO range when random (in Hz) #(1000 in old repo)
    )

    EsN0_range: np.ndarray = np.arange(0, 30, 1)

    # Lowpass filter parameters
    taps: np.ndarray = None  # specify None to make the simulator recompute the filter based on below spec
    # taps: np.ndarray = None  # specify None to make the simulator recompute the filter based on below spec
    numtaps: int = 31
    cutoff: float = 75e3  # BIT_RATE * osr_rx / 2.0001  # or 2*BIT_RATE,...
    
    use_golay: bool = False

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

    ideal_preamble_detect = False

    use_dynamic_ppd = False # If false: new ppd, if true: old ppd with dynamic thresholding
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

    # def preamble_detect(self, y):
    #     """Detect a preamble computing the received energy (average on a window)."""
    #     L = 4 * self.osr_rx
    #     y_abs = np.abs(y)

    #     for i in range(0, int(len(y) / L)):
    #         sum_abs = np.sum(y_abs[i * L : (i + 1) * L])
    #         if sum_abs > (L - 1):  # fix threshold
    #             return i * L

    #     return None
    
    
    
    def preamble_detect(self, y):
        # print("Using correlation-based preamble detection on discriminator output (PPD)")
        """
        Detect the preamble in a received CPFSK signal using normalized correlation
        on the differential phase (FM discriminator output).

        Parameters
        ----------
        y : np.ndarray
            Received complex baseband signal, shape (N,)

        Returns
        -------
        int | None
            Index of the first sample JUST AFTER the detected preamble window,
            matching the convention of the old detector.
            Returns None if no detection is found.
        """

        y_ = np.asarray(y)
        ylen = len(y_)

        if ylen < 2:
            self.last_corr_norm = np.zeros(ylen, dtype=np.float64)
            self.last_disc = np.zeros(max(0, ylen - 1), dtype=np.float64)
            return None

        if not np.iscomplexobj(y_):
            y_ = y_.astype(np.complex64) + 0j
        else:
            y_ = y_.astype(np.complex64, copy=False)

        # Parameters
        R = int(self.osr_rx)                 # samples per symbol at RX
        pre_bits = np.asarray(self.preamble, dtype=np.int8)
        pre_bits = pre_bits[:16]
        corr_threshold = float(getattr(self, "corr_threshold", 0.58))
        require_peak = bool(getattr(self, "corr_require_peak", True))

        if R <= 0 or pre_bits.size == 0:
            self.last_corr_norm = np.zeros(ylen, dtype=np.float64)
            self.last_disc = np.zeros(max(0, ylen - 1), dtype=np.float64)
            return None

        # ------------------------------------------------------------
        # 1) FM discriminator / differential phase
        #    dphi[n] corresponds to transition between y[n] and y[n+1]
        # ------------------------------------------------------------
        dphi = np.angle(y_[1:] * np.conjugate(y_[:-1])).astype(np.float64)

        # Remove average to reduce CFO bias
        dphi = dphi - np.mean(dphi)

        self.last_disc = dphi.copy()

        # ------------------------------------------------------------
        # 2) Build reference in discriminator domain
        #    bit 0 -> -1, bit 1 -> +1, repeated R times
        #    Since dphi has one sample less than y, ref length is Np - 1
        # ------------------------------------------------------------
        ref_bits_pm = (2 * pre_bits - 1).astype(np.float64)   # 0/1 -> -1/+1
        ref = np.repeat(ref_bits_pm, R)

        # dphi over a preamble of Np IQ samples has length Np - 1
        ref = ref[:-1]

        # remove DC bias
        ref = ref - np.mean(ref)

        ref_energy = np.dot(ref, ref)
        if ref_energy <= 1e-15:
            self.last_corr_norm = np.zeros(ylen, dtype=np.float64)
            return None

        L = len(ref)   # = len(pre_bits)*R - 1

        if len(dphi) < L:
            self.last_corr_norm = np.zeros(ylen, dtype=np.float64)
            return None

        # ------------------------------------------------------------
        # 3) Normalized sliding correlation on dphi
        #    Window start = k in dphi
        # ------------------------------------------------------------
        c_valid = np.convolve(dphi, ref[::-1], mode="valid")
        seg_energy = np.convolve(dphi * dphi, np.ones(L, dtype=np.float64), mode="valid")

        eps = 1e-12
        val_valid = np.abs(c_valid) / np.sqrt((seg_energy + eps) * (ref_energy + eps))

        # Store a debug array aligned with y end indices
        corr_norm = np.zeros(ylen, dtype=np.float64)

        # For a dphi window starting at k:
        # - dphi window ends at k + L - 1
        # - corresponding y window ends at k + L
        end_idx_y = np.arange(L, ylen, dtype=np.int64)
        corr_norm[end_idx_y] = val_valid
        self.last_corr_norm = corr_norm

        # ------------------------------------------------------------
        # 4) Detection rule
        #    Prefer first local peak above threshold.
        #    Fallback: first threshold crossing.
        # ------------------------------------------------------------
        above = np.flatnonzero(val_valid >= corr_threshold)
        if above.size == 0:
            return None

        if require_peak:
            last = len(val_valid) - 1
            peaks = []
            for k in above:
                left_ok = (k == 0) or (val_valid[k] >= val_valid[k - 1])
                right_ok = (k == last) or (val_valid[k] > val_valid[k + 1])
                if left_ok and right_ok:
                    peaks.append(k)

            if len(peaks) > 0:
                k_det = int(peaks[0])     # first detected local peak
            else:
                k_det = int(above[0])     # fallback
        else:
            k_det = int(above[0])

        # ------------------------------------------------------------
        # 5) Return convention
        #    If preamble starts at sample k_det in y and spans len(pre_bits)*R samples,
        #    return the first sample just AFTER the preamble.
        # ------------------------------------------------------------
        first_idx = int(k_det + len(pre_bits) * R)

        if first_idx >= ylen:
            return None

        return first_idx

    ideal_cfo_estimation = True
    
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
    


    ideal_sto_estimation = True

    def sto_estimation(self, y):
        """Estimates symbol timing (fractional) based on phase shifts."""
        R = self.osr_rx

        # Computation of derivatives of phase function
        phase_function = np.unwrap(np.angle(y))
        phase_derivative_1 = phase_function[1:] - phase_function[:-1]
        phase_derivative_2 = np.abs(phase_derivative_1[1:] - phase_derivative_1[:-1])

        sum_der_saved = -np.inf
        save_i = 0
        for i in range(0, R):
            sum_der = np.sum(phase_derivative_2[i::R])  # Sum every R samples

            if sum_der > sum_der_saved:
                sum_der_saved = sum_der
                save_i = i
                
        # print(f"sto est = {np.mod(save_i, R)}")

        return np.mod(save_i + 1, R)
    
    
   
    
    # ! utiliser ce truc là, bonnes perfs et on garde le même preambule
    def sto_estimation(self, y):
        R = self.osr_rx
        
        search_len = 32 * R
        y_segment = y[:search_len]
        
        # print(f"y segment = {y_segment}")
        
        discriminator_out = y_segment[1:] * np.conj(y_segment[:-1])
        disc_phase = np.angle(discriminator_out)

        n_template_bits = 16 # 12 taille opti pour RMSE
        dotting_bits = np.resize([1, 0], n_template_bits) 
        tx_syms = 2 * dotting_bits - 1
        ref_pattern = np.repeat(tx_syms, R)



        correlation = signal.correlate(disc_phase, ref_pattern, mode='valid')
        
        # 5. Find the Peak
        # The peak index represents the best alignment point
        peak_index = np.argmax(np.abs(correlation))
        
        # 6. Return Fractional Offset
        # This tells us where the symbol boundary is relative to our first sample
        # print(f"sto est = {np.mod(peak_index, R)}")
        return np.mod(peak_index, R)
    
   
    
    
    
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
    
    
    
    def golay_encode_if_enabled(self, bits):
        """Encodes bits only if use_golay is True."""
        if not self.use_golay:
            return bits
        
        # Ensure length is multiple of 12 for Golay (24,12)
        padding_len = (12 - (len(bits) % 12)) % 12
        if padding_len > 0:
            bits = np.concatenate([bits, np.zeros(padding_len, dtype=int)])
            
        reshaped = bits.reshape(-1, 12)
        encoded = (reshaped @ G_MAT) % 2
        return encoded.flatten()

    def golay_decode_if_enabled(self, bits, original_len):
        """Decodes and corrects bits only if use_golay is True."""
        if not self.use_golay:
            return bits[:original_len]
        
        # Safety check: if bits is empty or too short for one block
        if bits is None or len(bits) < 24:
            return np.zeros(original_len, dtype=int) # Return zeros to avoid crash
        
        n_blocks = len(bits) // 24
        reshaped = bits[:n_blocks*24].reshape(n_blocks, 24)
        decoded_list = []

        for block in reshaped:
            s = tuple((block @ H_MAT.T) % 2)
            error_pattern = SYNDROME_TABLE.get(s, np.zeros(24, dtype=int))
            corrected = (block + error_pattern) % 2
            decoded_list.append(corrected[:12])
            
        if not decoded_list: # Final check before concatenation
            return np.zeros(original_len, dtype=int)
            
        decoded = np.concatenate(decoded_list)
        return decoded[:original_len]