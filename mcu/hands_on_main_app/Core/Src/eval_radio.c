/*
 * eval_radio.c
 */
/*
#include <adc_dblbuf.h>
#include "eval_radio.h"
#include "config.h"
#include "main.h"
#include "s2lp.h"


void eval_radio(void)
{
	DEBUG_PRINT("[DBG] Radio evaluation mode\r\n");

	uint8_t buf[PAYLOAD_LEN];
	for (uint16_t i=0; i < PAYLOAD_LEN; i++) {
		buf[i] = (uint8_t) (i & 0xFF);
	}

	for (int32_t lvl = MIN_PA_LEVEL; lvl <= MAX_PA_LEVEL; lvl=lvl+STEP_PA_LEVEL) {
		btn_press = 0;
		DEBUG_PRINT("=== Press button B1 to start evaluation at %ld dBm\r\n", lvl);
		while (!btn_press) {
			__WFI();
		}

		S2LP_SetPALeveldBm(lvl);
		DEBUG_PRINT("=== Configured PA level to %ld dBm, sending %d packets at this level\r\n", lvl, N_PACKETS);

		for (uint16_t i=0; i < N_PACKETS; i++) {
			HAL_StatusTypeDef err = S2LP_Send(buf, PAYLOAD_LEN);
			if (err) {
				Error_Handler();
			}

			if (BLINK_LED==1){
				HAL_GPIO_WritePin(GPIOB, LD2_Pin, GPIO_PIN_SET);
				HAL_Delay(PACKET_DELAY>>1);
				HAL_GPIO_WritePin(GPIOB, LD2_Pin, GPIO_PIN_RESET);
				HAL_Delay(PACKET_DELAY>>1);
			} else{
				HAL_Delay(PACKET_DELAY);
			}
		}
	}

	DEBUG_PRINT("=== Finished evaluation, reset the board to run again\r\n");
	while (1);
}

*/

/*
 * eval_radio.c
 */
/*
#include <adc_dblbuf.h>
#include "eval_radio.h"
#include "config.h"
#include "main.h"
#include "s2lp.h"

// --- Hamming Bit Helpers ---
static inline uint8_t get_bit(const uint8_t *data, int bit_idx) {
    return (data[bit_idx / 8] >> (7 - (bit_idx % 8))) & 1;
}

static inline void set_bit(uint8_t *data, int bit_idx, uint8_t val) {
    if (val) data[bit_idx / 8] |= (1 << (7 - (bit_idx % 8)));
    else     data[bit_idx / 8] &= ~(1 << (7 - (bit_idx % 8)));
}

// --- Hamming (31, 26) Encoder ---
static void encode_hamming_block(const uint8_t *in_buf, int in_start_bit, int in_len, uint8_t *out_buf, int out_start_bit) {
    uint32_t out_word = 0;
    int d_idx = 0;

    // 1. Place data bits (skip parity positions 1, 2, 4, 8, 16)
    for (int i = 1; i <= 31; i++) {
        if (i == 1 || i == 2 || i == 4 || i == 8 || i == 16) continue;
        int bit_val = 0;
        if (d_idx < in_len) {
            bit_val = get_bit(in_buf, in_start_bit + d_idx);
        }
        if (bit_val) out_word |= (1UL << i);
        d_idx++;
    }

    // 2. Calculate the 5 parity bits
    for (int p = 0; p < 5; p++) {
        int p_pos = 1 << p;
        int parity = 0;
        for (int i = 1; i <= 31; i++) {
            if (i & p_pos) parity ^= ((out_word >> i) & 1);
        }
        if (parity) out_word |= (1UL << p_pos);
    }

    // 3. Write 31 bits to output buffer
    for (int i = 1; i <= 31; i++) {
        int bit_val = (out_word >> i) & 1;
        set_bit(out_buf, out_start_bit + i - 1, bit_val);
    }
}


void eval_radio(void)
{
	DEBUG_PRINT("[DBG] Radio evaluation mode\r\n");

	uint8_t buf[PAYLOAD_LEN];
	for (uint16_t i=0; i < PAYLOAD_LEN; i++) {
		buf[i] = (uint8_t) (i & 0xFF);
	}

	// --- Calculate Encoded Payload Details ---
	int total_data_bits = PAYLOAD_LEN * 8;
	int num_blocks = (total_data_bits + 25) / 26; // Ceil division by 26
	int encoded_bits = num_blocks * 31;
	int encoded_bytes = (encoded_bits + 7) / 8;   // Ceil division by 8

	uint8_t enc_buf[150] = {0}; // 150 is a safe max size for up to ~115 bytes input

	// Encode all blocks
	for (int i = 0; i < num_blocks; i++) {
		int bits_left = total_data_bits - (i * 26);
		int bits_to_encode = (bits_left < 26) ? bits_left : 26;
		encode_hamming_block(buf, i * 26, bits_to_encode, enc_buf, i * 31);
	}

	for (int32_t lvl = MIN_PA_LEVEL; lvl <= MAX_PA_LEVEL; lvl=lvl+STEP_PA_LEVEL) {
		btn_press = 0;
		DEBUG_PRINT("=== Press button B1 to start evaluation at %ld dBm\r\n", lvl);
		while (!btn_press) {
			__WFI();
		}

		S2LP_SetPALeveldBm(lvl);
		DEBUG_PRINT("=== Configured PA level to %ld dBm, sending %d packets at this level\r\n", lvl, N_PACKETS);

		for (uint16_t i=0; i < N_PACKETS; i++) {
            // SEND THE ENCODED BUFFER INSTEAD OF ORIGINAL BUF
			HAL_StatusTypeDef err = S2LP_Send(enc_buf, encoded_bytes);
			if (err) {
				Error_Handler();
			}

			if (BLINK_LED==1){
				HAL_GPIO_WritePin(GPIOB, LD2_Pin, GPIO_PIN_SET);
				HAL_Delay(PACKET_DELAY>>1);
				HAL_GPIO_WritePin(GPIOB, LD2_Pin, GPIO_PIN_RESET);
				HAL_Delay(PACKET_DELAY>>1);
			} else{
				HAL_Delay(PACKET_DELAY);
			}
		}
	}

	DEBUG_PRINT("=== Finished evaluation, reset the board to run again\r\n");
	while (1);
}
*/




/*
 * eval_radio.c
 */

#include <adc_dblbuf.h>
#include "eval_radio.h"
#include "config.h"
#include "main.h"
#include "s2lp.h"

#if USE_HAMMING == 1
// --- Hamming Bit Helpers ---
static inline uint8_t get_bit(const uint8_t *data, int bit_idx) {
    return (data[bit_idx / 8] >> (7 - (bit_idx % 8))) & 1;
}

static inline void set_bit(uint8_t *data, int bit_idx, uint8_t val) {
    if (val) data[bit_idx / 8] |= (1 << (7 - (bit_idx % 8)));
    else     data[bit_idx / 8] &= ~(1 << (7 - (bit_idx % 8)));
}

// --- Hamming (31, 26) Encoder ---
static void encode_hamming_block(const uint8_t *in_buf, int in_start_bit, int in_len, uint8_t *out_buf, int out_start_bit) {
    uint32_t out_word = 0;
    int d_idx = 0;

    // 1. Place data bits (skip parity positions 1, 2, 4, 8, 16)
    for (int i = 1; i <= 31; i++) {
        if (i == 1 || i == 2 || i == 4 || i == 8 || i == 16) continue;
        int bit_val = 0;
        if (d_idx < in_len) {
            bit_val = get_bit(in_buf, in_start_bit + d_idx);
        }
        if (bit_val) out_word |= (1UL << i);
        d_idx++;
    }

    // 2. Calculate the 5 parity bits
    for (int p = 0; p < 5; p++) {
        int p_pos = 1 << p;
        int parity = 0;
        for (int i = 1; i <= 31; i++) {
            if (i & p_pos) parity ^= ((out_word >> i) & 1);
        }
        if (parity) out_word |= (1UL << p_pos);
    }

    // 3. Write 31 bits to output buffer
    for (int i = 1; i <= 31; i++) {
        int bit_val = (out_word >> i) & 1;
        set_bit(out_buf, out_start_bit + i - 1, bit_val);
    }
}
#endif


void eval_radio(void)
{
	DEBUG_PRINT("[DBG] Radio evaluation mode\r\n");

	uint8_t buf[PAYLOAD_LEN];
	for (uint16_t i=0; i < PAYLOAD_LEN; i++) {
		buf[i] = (uint8_t) (i & 0xFF);
	}

#if USE_HAMMING == 1
	// --- Calculate Encoded Payload Details ---
	int total_data_bits = PAYLOAD_LEN * 8;
	int num_blocks = (total_data_bits + 25) / 26; // Ceil division by 26
	int encoded_bits = num_blocks * 31;
	int encoded_bytes = (encoded_bits + 7) / 8;   // Ceil division by 8

	uint8_t enc_buf[150] = {0}; // 150 is a safe max size for up to ~115 bytes input

	// Encode all blocks
	for (int i = 0; i < num_blocks; i++) {
		int bits_left = total_data_bits - (i * 26);
		int bits_to_encode = (bits_left < 26) ? bits_left : 26;
		encode_hamming_block(buf, i * 26, bits_to_encode, enc_buf, i * 31);
	}
#endif

	for (int32_t lvl = MIN_PA_LEVEL; lvl <= MAX_PA_LEVEL; lvl=lvl+STEP_PA_LEVEL) {
		btn_press = 0;
		DEBUG_PRINT("=== Press button B1 to start evaluation at %ld dBm\r\n", lvl);
		while (!btn_press) {
			__WFI();
		}

		S2LP_SetPALeveldBm(lvl);
		DEBUG_PRINT("=== Configured PA level to %ld dBm, sending %d packets at this level\r\n", lvl, N_PACKETS);

		for (uint16_t i=0; i < N_PACKETS; i++) {
#if USE_HAMMING == 1
            // SEND THE ENCODED BUFFER
			HAL_StatusTypeDef err = S2LP_Send(enc_buf, encoded_bytes);
#else
            // SEND THE ORIGINAL RAW BUFFER
			HAL_StatusTypeDef err = S2LP_Send(buf, PAYLOAD_LEN);
#endif
			if (err) {
				Error_Handler();
			}

			if (BLINK_LED==1){
				HAL_GPIO_WritePin(GPIOB, LD2_Pin, GPIO_PIN_SET);
				HAL_Delay(PACKET_DELAY>>1);
				HAL_GPIO_WritePin(GPIOB, LD2_Pin, GPIO_PIN_RESET);
				HAL_Delay(PACKET_DELAY>>1);
			} else{
				HAL_Delay(PACKET_DELAY);
			}
		}
	}

	DEBUG_PRINT("=== Finished evaluation, reset the board to run again\r\n");
	while (1);
}
