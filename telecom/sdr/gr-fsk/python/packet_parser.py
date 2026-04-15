


# #!/usr/bin/env python
# #
# # Copyright 2021 UCLouvain.
# #

# from distutils.version import LooseVersion
# import math
# import numpy as np
# from gnuradio import gr

# from .utils import logging, measurements_logger

# def reflect_data(x, width):
#     if width == 8:
#         x = ((x & 0x55) << 1) | ((x & 0xAA) >> 1)
#         x = ((x & 0x33) << 2) | ((x & 0xCC) >> 2)
#         x = ((x & 0x0F) << 4) | ((x & 0xF0) >> 4)
#     elif width == 16:
#         x = ((x & 0x5555) << 1) | ((x & 0xAAAA) >> 1)
#         x = ((x & 0x3333) << 2) | ((x & 0xCCCC) >> 2)
#         x = ((x & 0x0F0F) << 4) | ((x & 0xF0F0) >> 4)
#         x = ((x & 0x00FF) << 8) | ((x & 0xFF00) >> 8)
#     elif width == 32:
#         x = ((x & 0x55555555) << 1) | ((x & 0xAAAAAAAA) >> 1)
#         x = ((x & 0x33333333) << 2) | ((x & 0xCCCCCCCC) >> 2)
#         x = ((x & 0x0F0F0F0F) << 4) | ((x & 0xF0F0F0F0) >> 4)
#         x = ((x & 0x00FF00FF) << 8) | ((x & 0xFF00FF00) >> 8)
#         x = ((x & 0x0000FFFF) << 16) | ((x & 0xFFFF0000) >> 16)
#     else:
#         raise ValueError("Unsupported width")
#     return x


# def crc_poly(data, n, poly, crc=0, ref_in=False, ref_out=False, xor_out=0):
#     g = 1 << n | poly  
#     for d in data:
#         if ref_in:
#             d = reflect_data(d, 8)
#         crc ^= d << (n - 8)
#         for _ in range(8):
#             crc <<= 1
#             if crc & (1 << n):
#                 crc ^= g
#     if ref_out:
#         crc = reflect_data(crc, n)
#     return crc ^ xor_out


# class packet_parser(gr.basic_block):

#     def __init__(self, hdr_len, payload_len, crc_len, address, log_payload, enable_log):
#         self.hdr_len = hdr_len
#         self.payload_len = payload_len 
#         self.crc_len = crc_len
#         self.address = address
#         self.log_payload = log_payload
#         self.enable_log = enable_log

#         self.num_blocks = (self.payload_len * 8) // 31 
#         self.decoded_len = (self.num_blocks * 26) // 8 

#         self.packet_len = self.hdr_len + self.payload_len + self.crc_len

#         gr.basic_block.__init__(
#             self,
#             name="packet_parser",
#             in_sig=[np.uint8],
#             out_sig=[(np.uint8, self.payload_len)], 
#         )
#         self.nb_packet = 0
#         self.nb_error = 0
#         self.logger = logging.getLogger("parser")
#         self.gr_version = gr.version()

#     def forecast(self, noutput_items, ninputs):
#         ninput_items_required = [0] * ninputs
#         for i in range(ninputs):
#             ninput_items_required[i] = self.packet_len + 1  
#         return ninput_items_required

#     def set_log_payload(self, log_payload):
#         self.log_payload = log_payload

#     def set_enable_log(self, enable_log):
#         self.enable_log = enable_log

#     def general_work(self, input_items, output_items):
#         input_bytes = input_items[0][: self.packet_len + 1]
#         self.consume_each(self.packet_len + 1)

#         b = np.unpackbits(input_bytes)

#         b_hdr = b[: self.hdr_len * 8]
#         v = np.abs(
#             np.correlate(b_hdr * 2 - 1, np.array(self.address) * 2 - 1, mode="full")
#         )
#         i = np.argmax(v) + 1

#         b_pkt = b[i : i + (self.payload_len + self.crc_len) * 8]
#         pkt_bytes = np.packbits(b_pkt)

#         encoded_payload = pkt_bytes[0 : self.payload_len]
#         crc = pkt_bytes[self.payload_len : self.payload_len + self.crc_len]

#         # ==========================================
#         # START OF DEBUG LOGGING
#         # ==========================================
#         self.logger.info(f"\n{'='*40}")
#         self.logger.info(f"PROCESSING PACKET {self.nb_packet + 1}")
#         self.logger.info(f"{'='*40}")
#         self.logger.info(f"[BEFORE DECODING] Raw Encoded Payload ({len(encoded_payload)} bytes):")
#         self.logger.info(f"{encoded_payload.tolist()}")

#         # --- HAMMING DECODING & ERROR CORRECTION ---
#         enc_bits = np.unpackbits(encoded_payload)
#         dec_bits = []
#         corrected_enc_bits = []
        
#         corrected_bits_count = 0
#         corrected_byte_positions = []

#         for j in range(self.num_blocks):
#             block = enc_bits[j * 31 : (j + 1) * 31].copy()
#             if len(block) == 31:
#                 # 1. Check Syndrome
#                 syndrome = 0
#                 for p in range(5):
#                     p_pos = 1 << p
#                     parity = 0
#                     for k in range(1, 32):
#                         if (k & p_pos) != 0:
#                             parity ^= block[k - 1]
#                     if parity != 0:
#                         syndrome |= p_pos
                
#                 # 2. Correct Bit Error if detected
#                 if 0 < syndrome <= 31:
#                     corrected_bits_count += 1
                    
#                     # Calculate exact byte position in the 121-byte array
#                     global_bit_idx = (j * 31) + (syndrome - 1)
#                     byte_idx = global_bit_idx // 8
                    
#                     # Add to list if it's not already there (multiple bit errors could theoretically land in the same byte across block boundaries)
#                     if byte_idx not in corrected_byte_positions:
#                         corrected_byte_positions.append(byte_idx)
                        
#                     block[syndrome - 1] ^= 1 

#                 corrected_enc_bits.extend(block)

#                 # 3. Extract 26 Data Bits
#                 for k in range(1, 32):
#                     if k not in (1, 2, 4, 8, 16):
#                         dec_bits.append(block[k - 1])

#         # Pack padded corrected array to check S2LP Hardware CRC accurately
#         padding_len = (self.payload_len * 8) - len(corrected_enc_bits)
#         if padding_len > 0:
#             corrected_enc_bits.extend(enc_bits[-padding_len:])
            
#         corrected_encoded_payload = np.packbits(corrected_enc_bits)

#         # Truncate and pack purely decoded 100-byte data
#         dec_bits = dec_bits[:self.decoded_len * 8]
#         decoded_payload = np.packbits(dec_bits)

#         # ==========================================
#         # END OF DECODING LOGGING
#         # ==========================================
#         self.logger.info(f"[STATS] Total bits corrected by Hamming: {corrected_bits_count}")
#         if corrected_bits_count > 0:
#             self.logger.info(f"[STATS] Errors were found and corrected in byte index(es): {corrected_byte_positions}")
        
#         self.logger.info(f"[AFTER DECODING] Clean Payload ({len(decoded_payload)} bytes):")
#         self.logger.info(f"{decoded_payload.tolist()}")

#         padded_output = np.zeros(self.payload_len, dtype=np.uint8)
#         padded_output[:self.decoded_len] = decoded_payload
#         output_items[0][0] = padded_output

#         # S2LP calculates CRC over the physical encoded bytes. Verify it against our corrected array.
#         crc_verif = crc_poly(
#             bytearray(corrected_encoded_payload),
#             8,
#             0x07,
#             crc=0xFF,
#             ref_in=False,
#             ref_out=False,
#             xor_out=0,
#         )

#         self.nb_packet += 1
#         is_correct = all(crc == crc_verif)
        
#         measurements_logger.info(
#             f"packet_number={self.nb_packet},correct={is_correct},corrected_bits={corrected_bits_count},corrected_bytes=[{','.join(map(str, corrected_byte_positions))}],payload=[{','.join(map(str, decoded_payload))}]"
#         )
        
#         if is_correct:
#             if self.log_payload:
#                 self.logger.info(f"[RESULT] Packet {self.nb_packet} demodulated successfully (CRC: {crc.tolist()})")
            
#             if self.enable_log:
#                 self.logger.info(f"{self.nb_packet} packets received with {self.nb_error} error(s)")
#             return 1
#         else:
#             if self.log_payload:
#                 self.logger.error(f"[RESULT] Incorrect CRC, packet dropped. (Received CRC: {crc.tolist()} | Expected: [{crc_verif}])")
#             self.nb_error += 1
#             if self.enable_log:
#                 self.logger.info(f"{self.nb_packet} packets received with {self.nb_error} error(s)")
#             return 0



# #!/usr/bin/env python
# #
# # Copyright 2021 UCLouvain.
# #

# from distutils.version import LooseVersion
# import math
# import numpy as np
# from gnuradio import gr

# from .utils import logging, measurements_logger

# # ==========================================
# # RUNTIME CONFIGURATION
# # ==========================================
# # Set to True to enable Hamming(31,26) decoding. Set to False for raw transmission.
# # Make sure to update the 'Payload Length' in the GNU Radio GUI accordingly!
# # (e.g., 121 when True, 100 when False)
# USE_HAMMING = False 
# # ==========================================


# def reflect_data(x, width):
#     if width == 8:
#         x = ((x & 0x55) << 1) | ((x & 0xAA) >> 1)
#         x = ((x & 0x33) << 2) | ((x & 0xCC) >> 2)
#         x = ((x & 0x0F) << 4) | ((x & 0xF0) >> 4)
#     elif width == 16:
#         x = ((x & 0x5555) << 1) | ((x & 0xAAAA) >> 1)
#         x = ((x & 0x3333) << 2) | ((x & 0xCCCC) >> 2)
#         x = ((x & 0x0F0F) << 4) | ((x & 0xF0F0) >> 4)
#         x = ((x & 0x00FF) << 8) | ((x & 0xFF00) >> 8)
#     elif width == 32:
#         x = ((x & 0x55555555) << 1) | ((x & 0xAAAAAAAA) >> 1)
#         x = ((x & 0x33333333) << 2) | ((x & 0xCCCCCCCC) >> 2)
#         x = ((x & 0x0F0F0F0F) << 4) | ((x & 0xF0F0F0F0) >> 4)
#         x = ((x & 0x00FF00FF) << 8) | ((x & 0xFF00FF00) >> 8)
#         x = ((x & 0x0000FFFF) << 16) | ((x & 0xFFFF0000) >> 16)
#     else:
#         raise ValueError("Unsupported width")
#     return x


# def crc_poly(data, n, poly, crc=0, ref_in=False, ref_out=False, xor_out=0):
#     g = 1 << n | poly  
#     for d in data:
#         if ref_in:
#             d = reflect_data(d, 8)
#         crc ^= d << (n - 8)
#         for _ in range(8):
#             crc <<= 1
#             if crc & (1 << n):
#                 crc ^= g
#     if ref_out:
#         crc = reflect_data(crc, n)
#     return crc ^ xor_out


# class packet_parser(gr.basic_block):

#     def __init__(self, hdr_len, payload_len, crc_len, address, log_payload, enable_log):
#         self.hdr_len = hdr_len
#         self.payload_len = payload_len 
#         self.crc_len = crc_len
#         self.address = address
#         self.log_payload = log_payload
#         self.enable_log = enable_log
#         self.use_hamming = USE_HAMMING

#         if self.use_hamming:
#             self.num_blocks = (self.payload_len * 8) // 31 
#             self.decoded_len = (self.num_blocks * 26) // 8 
#         else:
#             self.num_blocks = 0
#             self.decoded_len = self.payload_len

#         self.packet_len = self.hdr_len + self.payload_len + self.crc_len

#         gr.basic_block.__init__(
#             self,
#             name="packet_parser",
#             in_sig=[np.uint8],
#             out_sig=[(np.uint8, self.payload_len)], 
#         )
#         self.nb_packet = 0
#         self.nb_error = 0
#         self.logger = logging.getLogger("parser")
#         self.gr_version = gr.version()

#     def forecast(self, noutput_items, ninputs):
#         ninput_items_required = [0] * ninputs
#         for i in range(ninputs):
#             ninput_items_required[i] = self.packet_len + 1  
#         return ninput_items_required

#     def set_log_payload(self, log_payload):
#         self.log_payload = log_payload

#     def set_enable_log(self, enable_log):
#         self.enable_log = enable_log

#     def general_work(self, input_items, output_items):
#         input_bytes = input_items[0][: self.packet_len + 1]
#         self.consume_each(self.packet_len + 1)

#         b = np.unpackbits(input_bytes)

#         b_hdr = b[: self.hdr_len * 8]
#         v = np.abs(
#             np.correlate(b_hdr * 2 - 1, np.array(self.address) * 2 - 1, mode="full")
#         )
#         i = np.argmax(v) + 1

#         b_pkt = b[i : i + (self.payload_len + self.crc_len) * 8]
#         pkt_bytes = np.packbits(b_pkt)

#         encoded_payload = pkt_bytes[0 : self.payload_len]
#         crc = pkt_bytes[self.payload_len : self.payload_len + self.crc_len]

#         self.logger.info(f"\n{'='*40}")
#         self.logger.info(f"PROCESSING PACKET {self.nb_packet + 1} | HAMMING: {'ON' if self.use_hamming else 'OFF'}")
#         self.logger.info(f"{'='*40}")
#         self.logger.info(f"[BEFORE DECODING] Raw RF Payload ({len(encoded_payload)} bytes):")
#         self.logger.info(f"{encoded_payload.tolist()}")

#         corrected_bits_count = 0
#         corrected_byte_positions = []

#         if self.use_hamming:
#             # --- HAMMING DECODING & ERROR CORRECTION ---
#             enc_bits = np.unpackbits(encoded_payload)
#             dec_bits = []
#             corrected_enc_bits = []

#             for j in range(self.num_blocks):
#                 block = enc_bits[j * 31 : (j + 1) * 31].copy()
#                 if len(block) == 31:
#                     # 1. Check Syndrome
#                     syndrome = 0
#                     for p in range(5):
#                         p_pos = 1 << p
#                         parity = 0
#                         for k in range(1, 32):
#                             if (k & p_pos) != 0:
#                                 parity ^= block[k - 1]
#                         if parity != 0:
#                             syndrome |= p_pos
                    
#                     # 2. Correct Bit Error if detected
#                     if 0 < syndrome <= 31:
#                         corrected_bits_count += 1
#                         global_bit_idx = (j * 31) + (syndrome - 1)
#                         byte_idx = global_bit_idx // 8
#                         if byte_idx not in corrected_byte_positions:
#                             corrected_byte_positions.append(byte_idx)
                            
#                         block[syndrome - 1] ^= 1 

#                     corrected_enc_bits.extend(block)

#                     # 3. Extract 26 Data Bits
#                     for k in range(1, 32):
#                         if k not in (1, 2, 4, 8, 16):
#                             dec_bits.append(block[k - 1])

#             # Pack padded corrected array to check S2LP Hardware CRC accurately
#             padding_len = (self.payload_len * 8) - len(corrected_enc_bits)
#             if padding_len > 0:
#                 corrected_enc_bits.extend(enc_bits[-padding_len:])
                
#             corrected_encoded_payload = np.packbits(corrected_enc_bits)

#             # Truncate and pack purely decoded 100-byte data
#             dec_bits = dec_bits[:self.decoded_len * 8]
#             decoded_payload = np.packbits(dec_bits)
            
#         else:
#             # --- NO HAMMING (RAW PASS-THROUGH) ---
#             corrected_encoded_payload = encoded_payload
#             decoded_payload = encoded_payload

#         # ==========================================
#         # LOGGING & OUTPUT
#         # ==========================================
#         if self.use_hamming:
#             self.logger.info(f"[STATS] Total bits corrected by Hamming: {corrected_bits_count}")
#             if corrected_bits_count > 0:
#                 self.logger.info(f"[STATS] Errors were found and corrected in byte index(es): {corrected_byte_positions}")
        
#         self.logger.info(f"[AFTER DECODING] Clean Payload ({len(decoded_payload)} bytes):")
#         self.logger.info(f"{decoded_payload.tolist()}")

#         # Pad output to match GRC GUI length expectation
#         padded_output = np.zeros(self.payload_len, dtype=np.uint8)
#         padded_output[:self.decoded_len] = decoded_payload
#         output_items[0][0] = padded_output

#         # S2LP calculates CRC over the physical encoded bytes.
#         crc_verif = crc_poly(
#             bytearray(corrected_encoded_payload),
#             8,
#             0x07,
#             crc=0xFF,
#             ref_in=False,
#             ref_out=False,
#             xor_out=0,
#         )

#         self.nb_packet += 1
#         is_correct = all(crc == crc_verif)
        
#         # Log to measurements file
#         if self.use_hamming:
#             measurements_logger.info(
#                 f"packet_number={self.nb_packet},correct={is_correct},corrected_bits={corrected_bits_count},corrected_bytes=[{','.join(map(str, corrected_byte_positions))}],payload=[{','.join(map(str, decoded_payload))}]"
#             )
#         else:
#             measurements_logger.info(
#                 f"packet_number={self.nb_packet},correct={is_correct},payload=[{','.join(map(str, decoded_payload))}]"
#             )
        
#         if is_correct:
#             if self.log_payload:
#                 self.logger.info(f"[RESULT] Packet {self.nb_packet} demodulated successfully (CRC: {crc.tolist()})")
            
#             if self.enable_log:
#                 self.logger.info(f"{self.nb_packet} packets received with {self.nb_error} error(s)")
#             return 1
#         else:
#             if self.log_payload:
#                 self.logger.error(f"[RESULT] Incorrect CRC, packet dropped. (Received CRC: {crc.tolist()} | Expected: [{crc_verif}])")
#             self.nb_error += 1
#             if self.enable_log:
#                 self.logger.info(f"{self.nb_packet} packets received with {self.nb_error} error(s)")
#             return 0




# #!/usr/bin/env python
# #
# # Copyright 2021 UCLouvain.
# #

# from distutils.version import LooseVersion
# import math
# import numpy as np
# from gnuradio import gr

# from .utils import logging, measurements_logger

# # ==========================================
# # RUNTIME CONFIGURATION
# # ==========================================
# # Set to True to enable Hamming(31,26) decoding. Set to False for raw transmission.
# # Make sure to update the 'Payload Length' in the GNU Radio GUI accordingly!
# # (e.g., 985 when True, 824 when False)
# USE_HAMMING = True

# # Set this to the exact RAW byte length you expect to recover
# # Main App: 8 (Header) + 800 (Payload) + 16 (MAC) = 824 bytes
# TARGET_RAW_LEN = 824
# # ==========================================


# def reflect_data(x, width):
#     if width == 8:
#         x = ((x & 0x55) << 1) | ((x & 0xAA) >> 1)
#         x = ((x & 0x33) << 2) | ((x & 0xCC) >> 2)
#         x = ((x & 0x0F) << 4) | ((x & 0xF0) >> 4)
#     elif width == 16:
#         x = ((x & 0x5555) << 1) | ((x & 0xAAAA) >> 1)
#         x = ((x & 0x3333) << 2) | ((x & 0xCCCC) >> 2)
#         x = ((x & 0x0F0F) << 4) | ((x & 0xF0F0) >> 4)
#         x = ((x & 0x00FF) << 8) | ((x & 0xFF00) >> 8)
#     elif width == 32:
#         x = ((x & 0x55555555) << 1) | ((x & 0xAAAAAAAA) >> 1)
#         x = ((x & 0x33333333) << 2) | ((x & 0xCCCCCCCC) >> 2)
#         x = ((x & 0x0F0F0F0F) << 4) | ((x & 0xF0F0F0F0) >> 4)
#         x = ((x & 0x00FF00FF) << 8) | ((x & 0xFF00FF00) >> 8)
#         x = ((x & 0x0000FFFF) << 16) | ((x & 0xFFFF0000) >> 16)
#     else:
#         raise ValueError("Unsupported width")
#     return x


# def crc_poly(data, n, poly, crc=0, ref_in=False, ref_out=False, xor_out=0):
#     g = 1 << n | poly  
#     for d in data:
#         if ref_in:
#             d = reflect_data(d, 8)
#         crc ^= d << (n - 8)
#         for _ in range(8):
#             crc <<= 1
#             if crc & (1 << n):
#                 crc ^= g
#     if ref_out:
#         crc = reflect_data(crc, n)
#     return crc ^ xor_out


# class packet_parser(gr.basic_block):

#     def __init__(self, hdr_len, payload_len, crc_len, address, log_payload, enable_log):
#         self.hdr_len = hdr_len
#         self.payload_len = payload_len 
#         self.crc_len = crc_len
#         self.address = address
#         self.log_payload = log_payload
#         self.enable_log = enable_log
#         self.use_hamming = USE_HAMMING

#         if self.use_hamming:
#             self.num_blocks = (self.payload_len * 8) // 31 
#             self.decoded_len = TARGET_RAW_LEN 
#         else:
#             self.num_blocks = 0
#             self.decoded_len = self.payload_len

#         self.packet_len = self.hdr_len + self.payload_len + self.crc_len

#         gr.basic_block.__init__(
#             self,
#             name="packet_parser",
#             in_sig=[np.uint8],
#             out_sig=[(np.uint8, self.payload_len)], 
#         )
#         self.nb_packet = 0
#         self.nb_error = 0
#         self.logger = logging.getLogger("parser")
#         self.gr_version = gr.version()

#     def forecast(self, noutput_items, ninputs):
#         ninput_items_required = [0] * ninputs
#         for i in range(ninputs):
#             ninput_items_required[i] = self.packet_len + 1  
#         return ninput_items_required

#     def set_log_payload(self, log_payload):
#         self.log_payload = log_payload

#     def set_enable_log(self, enable_log):
#         self.enable_log = enable_log

#     def general_work(self, input_items, output_items):
#         input_bytes = input_items[0][: self.packet_len + 1]
#         self.consume_each(self.packet_len + 1)

#         b = np.unpackbits(input_bytes)

#         b_hdr = b[: self.hdr_len * 8]
#         v = np.abs(
#             np.correlate(b_hdr * 2 - 1, np.array(self.address) * 2 - 1, mode="full")
#         )
#         i = np.argmax(v) + 1

#         b_pkt = b[i : i + (self.payload_len + self.crc_len) * 8]
#         pkt_bytes = np.packbits(b_pkt)

#         encoded_payload = pkt_bytes[0 : self.payload_len]
#         crc = pkt_bytes[self.payload_len : self.payload_len + self.crc_len]

#         self.logger.info(f"\n{'='*40}")
#         self.logger.info(f"PROCESSING PACKET {self.nb_packet + 1} | HAMMING: {'ON' if self.use_hamming else 'OFF'}")
#         self.logger.info(f"{'='*40}")
#         # Only log first 15 bytes to avoid console flooding on 985-byte arrays
#         self.logger.info(f"[BEFORE DECODING] Raw RF Payload Preview (First 15 of {len(encoded_payload)} bytes):")
#         self.logger.info(f"{encoded_payload[:15].tolist()}")

#         corrected_bits_count = 0
#         corrected_byte_positions = []

#         if self.use_hamming:
#             # --- HAMMING DECODING & ERROR CORRECTION ---
#             enc_bits = np.unpackbits(encoded_payload)
#             dec_bits = []
#             corrected_enc_bits = []

#             for j in range(self.num_blocks):
#                 block = enc_bits[j * 31 : (j + 1) * 31].copy()
#                 if len(block) == 31:
#                     # 1. Check Syndrome
#                     syndrome = 0
#                     for p in range(5):
#                         p_pos = 1 << p
#                         parity = 0
#                         for k in range(1, 32):
#                             if (k & p_pos) != 0:
#                                 parity ^= block[k - 1]
#                         if parity != 0:
#                             syndrome |= p_pos
                    
#                     # 2. Correct Bit Error if detected
#                     if 0 < syndrome <= 31:
#                         corrected_bits_count += 1
#                         global_bit_idx = (j * 31) + (syndrome - 1)
#                         byte_idx = global_bit_idx // 8
#                         if byte_idx not in corrected_byte_positions:
#                             corrected_byte_positions.append(byte_idx)
                            
#                         block[syndrome - 1] ^= 1 

#                     corrected_enc_bits.extend(block)

#                     # 3. Extract 26 Data Bits
#                     for k in range(1, 32):
#                         if k not in (1, 2, 4, 8, 16):
#                             dec_bits.append(block[k - 1])

#             # Pack padded corrected array to check S2LP Hardware CRC accurately
#             padding_len = (self.payload_len * 8) - len(corrected_enc_bits)
#             if padding_len > 0:
#                 corrected_enc_bits.extend(enc_bits[-padding_len:])
                
#             corrected_encoded_payload = np.packbits(corrected_enc_bits)

#             # Truncate and pack purely decoded app data (824 bytes)
#             dec_bits = dec_bits[:self.decoded_len * 8]
#             decoded_payload = np.packbits(dec_bits)
            
#         else:
#             # --- NO HAMMING (RAW PASS-THROUGH) ---
#             corrected_encoded_payload = encoded_payload
#             decoded_payload = encoded_payload

#         # ==========================================
#         # LOGGING & OUTPUT
#         # ==========================================
#         if self.use_hamming:
#             self.logger.info(f"[STATS] Total bits corrected by Hamming: {corrected_bits_count}")
#             if corrected_bits_count > 0:
#                 self.logger.info(f"[STATS] Errors were found and corrected in byte index(es): {corrected_byte_positions}")
        
#         self.logger.info(f"[AFTER DECODING] Clean Payload Preview (First 15 of {len(decoded_payload)} bytes):")
#         self.logger.info(f"{decoded_payload[:15].tolist()}")

#         # Pad output to match GRC GUI length expectation to prevent vector mismatch errors
#         padded_output = np.zeros(self.payload_len, dtype=np.uint8)
#         padded_output[:self.decoded_len] = decoded_payload
#         output_items[0][0] = padded_output

#         # S2LP calculates CRC over the physical encoded bytes.
#         crc_verif = crc_poly(
#             bytearray(corrected_encoded_payload),
#             8,
#             0x07,
#             crc=0xFF,
#             ref_in=False,
#             ref_out=False,
#             xor_out=0,
#         )

#         self.nb_packet += 1
#         is_correct = all(crc == crc_verif)
        
#         # Log to measurements file (Removed payload printing to avoid massive 800-byte log lines)
#         if self.use_hamming:
#             measurements_logger.info(
#                 f"packet_number={self.nb_packet},correct={is_correct},corrected_bits={corrected_bits_count},corrected_bytes=[{','.join(map(str, corrected_byte_positions))}]"
#             )
#         else:
#             measurements_logger.info(
#                 f"packet_number={self.nb_packet},correct={is_correct}"
#             )
        
#         if is_correct:
#             if self.log_payload:
#                 self.logger.info(f"[RESULT] Packet {self.nb_packet} demodulated successfully (CRC: {crc.tolist()})")
            
#             if self.enable_log:
#                 self.logger.info(f"{self.nb_packet} packets received with {self.nb_error} error(s)")
#             return 1
#         else:
#             if self.log_payload:
#                 self.logger.error(f"[RESULT] Incorrect CRC, packet dropped. (Received CRC: {crc.tolist()} | Expected: [{crc_verif}])")
#             self.nb_error += 1
#             if self.enable_log:
#                 self.logger.info(f"{self.nb_packet} packets received with {self.nb_error} error(s)")
#             return 0

#!/usr/bin/env python
#
# Copyright 2021 UCLouvain.
#

import os
from distutils.version import LooseVersion
import math
import numpy as np
from gnuradio import gr

from .utils import logging, measurements_logger
# from dotenv import load_dotenv

# Load environment variables
# load_dotenv()

# ==========================================
# RUNTIME CONFIGURATION
# ==========================================
# Read from .env file (Defaults to False if not found)
# USE_HAMMING = os.environ.get("USE_HAMMING", "0") == "1"

# Main App Raw Size: 8 (Header) + 800 (Payload) + 16 (MAC) = 824 bytes
TARGET_RAW_LEN = 824
# ==========================================


USE_HAMMING = True
IS_EVAL_RADIO = False 

if IS_EVAL_RADIO:
    TARGET_RAW_LEN = 100 # Eval Radio sends exactly 100 bytes
else:
    TARGET_RAW_LEN = 824 # Main App sends 8 Header + 800 Payload + 16 MAC

def reflect_data(x, width):
    if width == 8:
        x = ((x & 0x55) << 1) | ((x & 0xAA) >> 1)
        x = ((x & 0x33) << 2) | ((x & 0xCC) >> 2)
        x = ((x & 0x0F) << 4) | ((x & 0xF0) >> 4)
    elif width == 16:
        x = ((x & 0x5555) << 1) | ((x & 0xAAAA) >> 1)
        x = ((x & 0x3333) << 2) | ((x & 0xCCCC) >> 2)
        x = ((x & 0x0F0F) << 4) | ((x & 0xF0F0) >> 4)
        x = ((x & 0x00FF) << 8) | ((x & 0xFF00) >> 8)
    elif width == 32:
        x = ((x & 0x55555555) << 1) | ((x & 0xAAAAAAAA) >> 1)
        x = ((x & 0x33333333) << 2) | ((x & 0xCCCCCCCC) >> 2)
        x = ((x & 0x0F0F0F0F) << 4) | ((x & 0xF0F0F0F0) >> 4)
        x = ((x & 0x00FF00FF) << 8) | ((x & 0xFF00FF00) >> 8)
        x = ((x & 0x0000FFFF) << 16) | ((x & 0xFFFF0000) >> 16)
    else:
        raise ValueError("Unsupported width")
    return x


def crc_poly(data, n, poly, crc=0, ref_in=False, ref_out=False, xor_out=0):
    g = 1 << n | poly  
    for d in data:
        if ref_in:
            d = reflect_data(d, 8)
        crc ^= d << (n - 8)
        for _ in range(8):
            crc <<= 1
            if crc & (1 << n):
                crc ^= g
    if ref_out:
        crc = reflect_data(crc, n)
    return crc ^ xor_out


class packet_parser(gr.basic_block):

    def __init__(self, hdr_len, payload_len, crc_len, address, log_payload, enable_log):
        self.hdr_len = hdr_len
        self.payload_len = payload_len 
        self.crc_len = crc_len
        self.address = address
        self.log_payload = log_payload
        self.enable_log = enable_log
        self.use_hamming = USE_HAMMING

        if self.use_hamming:
            self.num_blocks = (self.payload_len * 8) // 31 
            self.decoded_len = TARGET_RAW_LEN 
        else:
            self.num_blocks = 0
            self.decoded_len = self.payload_len

        self.packet_len = self.hdr_len + self.payload_len + self.crc_len

        gr.basic_block.__init__(
            self,
            name="packet_parser",
            in_sig=[np.uint8],
            # Reverted to full length so GNU Radio ZMQ Sink doesn't complain
            out_sig=[(np.uint8, self.payload_len)], 
        )
        self.nb_packet = 0
        self.nb_error = 0
        self.logger = logging.getLogger("parser")
        self.gr_version = gr.version()

    def forecast(self, noutput_items, ninputs):
        ninput_items_required = [0] * ninputs
        for i in range(ninputs):
            ninput_items_required[i] = self.packet_len + 1  
        return ninput_items_required

    def set_log_payload(self, log_payload):
        self.log_payload = log_payload

    def set_enable_log(self, enable_log):
        self.enable_log = enable_log

    def general_work(self, input_items, output_items):
        input_bytes = input_items[0][: self.packet_len + 1]
        self.consume_each(self.packet_len + 1)

        b = np.unpackbits(input_bytes)

        b_hdr = b[: self.hdr_len * 8]
        v = np.abs(
            np.correlate(b_hdr * 2 - 1, np.array(self.address) * 2 - 1, mode="full")
        )
        i = np.argmax(v) + 1

        b_pkt = b[i : i + (self.payload_len + self.crc_len) * 8]
        pkt_bytes = np.packbits(b_pkt)

        encoded_payload = pkt_bytes[0 : self.payload_len]
        crc = pkt_bytes[self.payload_len : self.payload_len + self.crc_len]

        self.logger.info(f"\n{'='*40}")
        self.logger.info(f"PROCESSING PACKET {self.nb_packet + 1} | HAMMING: {'ON' if self.use_hamming else 'OFF'}")
        self.logger.info(f"{'='*40}")

        corrected_bits_count = 0
        corrected_byte_positions = []

        if self.use_hamming:
            enc_bits = np.unpackbits(encoded_payload)
            dec_bits = []
            corrected_enc_bits = []

            for j in range(self.num_blocks):
                block = enc_bits[j * 31 : (j + 1) * 31].copy()
                if len(block) == 31:
                    syndrome = 0
                    for p in range(5):
                        p_pos = 1 << p
                        parity = 0
                        for k in range(1, 32):
                            if (k & p_pos) != 0:
                                parity ^= block[k - 1]
                        if parity != 0:
                            syndrome |= p_pos
                    
                    if 0 < syndrome <= 31:
                        corrected_bits_count += 1
                        global_bit_idx = (j * 31) + (syndrome - 1)
                        byte_idx = global_bit_idx // 8
                        if byte_idx not in corrected_byte_positions:
                            corrected_byte_positions.append(byte_idx)
                            
                        block[syndrome - 1] ^= 1 

                    corrected_enc_bits.extend(block)

                    for k in range(1, 32):
                        if k not in (1, 2, 4, 8, 16):
                            dec_bits.append(block[k - 1])

            padding_len = (self.payload_len * 8) - len(corrected_enc_bits)
            if padding_len > 0:
                corrected_enc_bits.extend(enc_bits[-padding_len:])
                
            corrected_encoded_payload = np.packbits(corrected_enc_bits)
            
            dec_bits = dec_bits[:self.decoded_len * 8]
            decoded_payload = np.packbits(dec_bits)
            
        else:
            corrected_encoded_payload = encoded_payload
            decoded_payload = encoded_payload

        if self.use_hamming:
            self.logger.info(f"[STATS] Total bits corrected by Hamming: {corrected_bits_count}")

        # Pad output with zeros to match GRC GUI length expectation
        padded_output = np.zeros(self.payload_len, dtype=np.uint8)
        padded_output[:self.decoded_len] = decoded_payload
        output_items[0][0] = padded_output

        crc_verif = crc_poly(
            bytearray(corrected_encoded_payload),
            8,
            0x07,
            crc=0xFF,
            ref_in=False,
            ref_out=False,
            xor_out=0,
        )

        self.nb_packet += 1
        is_correct = all(crc == crc_verif)
        
        if self.use_hamming:
            measurements_logger.info(
                f"packet_number={self.nb_packet},correct={is_correct},corrected_bits={corrected_bits_count},corrected_bytes=[{','.join(map(str, corrected_byte_positions))}]"
            )
        else:
            measurements_logger.info(
                f"packet_number={self.nb_packet},correct={is_correct}"
            )
        
        if is_correct:
            if self.log_payload:
                self.logger.info(f"[RESULT] Packet {self.nb_packet} demodulated successfully (CRC: {crc.tolist()})")
            
            if self.enable_log:
                self.logger.info(f"{self.nb_packet} packets received with {self.nb_error} error(s)")
            return 1
        else:
            if self.log_payload:
                self.logger.error(f"[RESULT] Incorrect CRC, packet dropped. (Received CRC: {crc.tolist()} | Expected: [{crc_verif}])")
            self.nb_error += 1
            if self.enable_log:
                self.logger.info(f"{self.nb_packet} packets received with {self.nb_error} error(s)")
            return 0