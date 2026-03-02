/*
 * packet.c
 */

//#include "aes_ref.h"
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







