/*
 * packet.h
 */
/*
#ifndef INC_PACKET_H_
#define INC_PACKET_H_

#include <stdint.h>
#include <stdlib.h>


#define PACKET_HEADER_LENGTH (1+1+2+4)
#define PACKET_TAG_LENGTH 16

#define PAYLOAD_LENGTH (sizeof(q15_t) * N_MELVECS * MELVEC_LENGTH)
#define PACKET_LENGTH (PACKET_HEADER_LENGTH + PAYLOAD_LENGTH + PACKET_TAG_LENGTH)

int make_packet(uint8_t *packet, size_t payload_len, uint8_t sender_id, uint32_t serial);

#endif /* INC_PACKET_H_ */


/*
 * packet.h
 */

#ifndef INC_PACKET_H_
#define INC_PACKET_H_

#include <stdint.h>
#include <stdlib.h>
#include "config.h"
#include "arm_math.h" // Required to define q15_t used in PAYLOAD_LENGTH

#define PACKET_HEADER_LENGTH (1+1+2+4)
#define PACKET_TAG_LENGTH 16

#define PAYLOAD_LENGTH (sizeof(q15_t) * N_MELVECS * MELVEC_LENGTH)
#define RAW_PACKET_LENGTH (PACKET_HEADER_LENGTH + PAYLOAD_LENGTH + PACKET_TAG_LENGTH)

// Dynamically scale the packet buffer memory allocation based on Hamming mode
#if USE_HAMMING == 1
#define PACKET_NUM_BLOCKS ((RAW_PACKET_LENGTH * 8 + 25) / 26)
#define ENCODED_PACKET_LENGTH ((PACKET_NUM_BLOCKS * 31 + 7) / 8)
#define PACKET_LENGTH ENCODED_PACKET_LENGTH
#else
#define PACKET_LENGTH RAW_PACKET_LENGTH
#endif

int make_packet(uint8_t *packet, size_t payload_len, uint8_t sender_id, uint32_t serial);

#endif /* INC_PACKET_H_ */

