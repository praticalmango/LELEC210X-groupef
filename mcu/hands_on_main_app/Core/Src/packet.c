/*
 * packet.c
 */
/*
#include "aes_ref.h"
#include "aes.h"
#include "config.h"
#include "packet.h"
#include "main.h"
#include "utils.h"

extern CRYP_HandleTypeDef hcryp;



const uint8_t AES_Key[16]  = {
                            0x00,0x00,0x00,0x00,
							0x00,0x00,0x00,0x00,
							0x00,0x00,0x00,0x00,
							0x00,0x00,0x00,0x00};







void tag_cbc_mac(uint8_t *tag, const uint8_t *msg, size_t msg_len) {
    // 4 * 32 bits = 16 octets pour l'état CBC
    uint32_t statew[4] = {0};

    // CORRECTION: Added '*' to make 'state' a pointer to the bytes of statew
    uint8_t *state = (uint8_t *) statew;

    size_t i;
    int j;

    // IV = 0...0 (déjà fait par l'initialisation de statew)

    // Parcours du message par blocs de 16 octets
    for (i = 0; i < msg_len; i += 16) {
        // XOR du bloc courant (paddé avec 0 si bloc partiel)
        for (j = 0; j < 16; j++) {
            uint8_t mbyte = 0;

            if (i + (size_t)j < msg_len) {
                mbyte = msg[i + (size_t)j];
            }

            state[j] ^= mbyte; // This now works!
        }

        // Chiffrement AES du state
        //AES128_encrypt(state, AES_Key);
        //HAL_CRYP_Encrypt(&hcryp, statew, 16, statew, HAL_MAX_DELAY);
        HAL_CRYPEx_AES(&hcryp, state, 16, state, HAL_MAX_DELAY);
    }

    // Copie du résultat dans le tag
    for (j = 0; j < 16; j++) {
        tag[j] = state[j];
    }
}

// Assumes payload is already in place in the packet
int make_packet(uint8_t *packet, size_t payload_len, uint8_t sender_id, uint32_t serial)
{
    size_t packet_len = payload_len + PACKET_HEADER_LENGTH + PACKET_TAG_LENGTH;

    // --- Header ---

    // r : reserved = 0
    packet[0] = 0x00;

    // emitter_id : 1 byte
    packet[1] = sender_id;

    // payload_length : 2 bytes, Big Endian
    packet[2] = (payload_len >> 8) & 0xFF;   // high byte
    packet[3] = payload_len & 0xFF;          // low byte

    // packet_serial : 4 bytes, Big Endian
    packet[4] = (serial >> 24) & 0xFF;
    packet[5] = (serial >> 16) & 0xFF;
    packet[6] = (serial >> 8)  & 0xFF;
    packet[7] = serial & 0xFF;

    // app_data est déjà présent à partir de packet[PACKET_HEADER_LENGTH]

    // --- Calcul du tag (MAC) sur header + payload ---
    tag_cbc_mac(
        packet + PACKET_HEADER_LENGTH + payload_len,  // où écrire le tag
        packet,                                       // message = header + payload
        PACKET_HEADER_LENGTH + payload_len
    );

    return packet_len;
}

*/

/*
 * packet.c
 */

#include "aes_ref.h"
#include "aes.h"
#include "config.h"
#include "packet.h"
#include "main.h"
#include "utils.h"
#include <string.h>

extern CRYP_HandleTypeDef hcryp;

const uint8_t AES_Key[16]  = {
                            0x00,0x00,0x00,0x00,
							0x00,0x00,0x00,0x00,
							0x00,0x00,0x00,0x00,
							0x00,0x00,0x00,0x00};


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

    for (int i = 1; i <= 31; i++) {
        if (i == 1 || i == 2 || i == 4 || i == 8 || i == 16) continue;
        int bit_val = 0;
        if (d_idx < in_len) {
            bit_val = get_bit(in_buf, in_start_bit + d_idx);
        }
        if (bit_val) out_word |= (1UL << i);
        d_idx++;
    }

    for (int p = 0; p < 5; p++) {
        int p_pos = 1 << p;
        int parity = 0;
        for (int i = 1; i <= 31; i++) {
            if (i & p_pos) parity ^= ((out_word >> i) & 1);
        }
        if (parity) out_word |= (1UL << p_pos);
    }

    for (int i = 1; i <= 31; i++) {
        int bit_val = (out_word >> i) & 1;
        set_bit(out_buf, out_start_bit + i - 1, bit_val);
    }
}
#endif


void tag_cbc_mac(uint8_t *tag, const uint8_t *msg, size_t msg_len) {
    uint32_t statew[4] = {0};
    uint8_t *state = (uint8_t *) statew;
    size_t i;
    int j;

    for (i = 0; i < msg_len; i += 16) {
        for (j = 0; j < 16; j++) {
            uint8_t mbyte = 0;
            if (i + (size_t)j < msg_len) {
                mbyte = msg[i + (size_t)j];
            }
            state[j] ^= mbyte;
        }
        HAL_CRYPEx_AES(&hcryp, state, 16, state, HAL_MAX_DELAY);
    }

    for (j = 0; j < 16; j++) {
        tag[j] = state[j];
    }
}

// Assumes payload is already in place in the packet
int make_packet(uint8_t *packet, size_t payload_len, uint8_t sender_id, uint32_t serial)
{
    // final_raw_len will be 824 for the main app
    size_t final_raw_len = payload_len + PACKET_HEADER_LENGTH + PACKET_TAG_LENGTH;

    // --- Header ---
    packet[0] = 0x00;
    packet[1] = sender_id;
    packet[2] = (payload_len >> 8) & 0xFF;
    packet[3] = payload_len & 0xFF;
    packet[4] = (serial >> 24) & 0xFF;
    packet[5] = (serial >> 16) & 0xFF;
    packet[6] = (serial >> 8)  & 0xFF;
    packet[7] = serial & 0xFF;

    // --- MAC ---
    tag_cbc_mac(
        packet + PACKET_HEADER_LENGTH + payload_len,
        packet,
        PACKET_HEADER_LENGTH + payload_len
    );

#if USE_HAMMING == 1
    int total_data_bits = final_raw_len * 8;
    int num_blocks = (total_data_bits + 25) / 26;
    int encoded_bits = num_blocks * 31;
    int encoded_bytes = (encoded_bits + 7) / 8;

    // Local buffer to hold encoded data before overwriting the packet array
    static uint8_t enc_buf[ENCODED_PACKET_LENGTH];
    memset(enc_buf, 0, encoded_bytes);

    // Encode all blocks
    for (int i = 0; i < num_blocks; i++) {
        int bits_left = total_data_bits - (i * 26);
        int bits_to_encode = (bits_left < 26) ? bits_left : 26;
        encode_hamming_block(packet, i * 26, bits_to_encode, enc_buf, i * 31);
    }

    // Copy encoded array back over the raw packet.
    // This is safe because 'packet' was allocated using the ENCODED_PACKET_LENGTH macro in packet.h!
    memcpy(packet, enc_buf, encoded_bytes);
    return encoded_bytes;
#else
    return final_raw_len;
#endif
}



