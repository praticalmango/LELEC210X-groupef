#include <adc_dblbuf.h>
#include "config.h"
#include "main.h"
#include "spectrogram.h"
#include "arm_math.h"
#include "utils.h"
#include "s2lp.h"
#include "packet.h"


static volatile uint16_t ADCDoubleBuf[2*ADC_BUF_SIZE]; /* ADC group regular conversion data (array of data) */
static volatile uint16_t* ADCData[2] = {&ADCDoubleBuf[0], &ADCDoubleBuf[ADC_BUF_SIZE]};
static volatile uint8_t ADCDataRdy[2] = {0, 0};

static volatile uint8_t cur_melvec = 0;
static q15_t mel_vectors[N_MELVECS][MELVEC_LENGTH];

static uint32_t packet_cnt = 0;

static volatile int32_t rem_n_bufs = 0;

// Energy tracking for adaptive threshold
#if (ENERGY_DETECTION_MODE == 1)
static long long energy_history[LONG_TERM_WINDOW_SIZE];  // Circular buffer for all energies
static int energy_hist_idx = 0;                            // Current write index
static int energy_hist_count = 0;                          // Number of valid entries
#endif

int StartADCAcq(int32_t n_bufs) {
	rem_n_bufs = n_bufs;
	cur_melvec = 0;
	if (rem_n_bufs != 0) {
		return HAL_ADC_Start_DMA(&hadc1, (uint32_t *)ADCDoubleBuf, 2*ADC_BUF_SIZE);
	} else {
		return HAL_OK;
	}
}

int IsADCFinished(void) {
	return (rem_n_bufs == 0);
}

static void StopADCAcq() {
	HAL_ADC_Stop_DMA(&hadc1);
}

static void print_spectrogram(void) {
#if (DEBUGP == 1)
	start_cycle_count();
	DEBUG_PRINT("Acquisition complete, sending the following FVs\r\n");
	for(unsigned int j=0; j < N_MELVECS; j++) {
		DEBUG_PRINT("FV #%u:\t", j+1);
		for(unsigned int i=0; i < MELVEC_LENGTH; i++) {
			DEBUG_PRINT("%.2f, ", q15_to_float(mel_vectors[j][i]));
		}
		DEBUG_PRINT("\r\n");
	}
	stop_cycle_count("Print FV");
#endif
}

static void print_encoded_packet(uint8_t *packet) {
#if (DEBUGP == 1)
	char hex_encoded_packet[2*PACKET_LENGTH+1];
	hex_encode(hex_encoded_packet, packet, PACKET_LENGTH);
	DEBUG_PRINT("DF:HEX:%s\r\n", hex_encoded_packet);
#endif
}

// Compute sum-of-squares energy of all mel coefficients (uses 64-bit accumulator)
static long long compute_mel_energy(void) {
    long long energy = 0;
    for (size_t i = 0; i < N_MELVECS; i++) {
        for (size_t j = 0; j < MELVEC_LENGTH; j++) {
            int32_t v = mel_vectors[i][j];
            long long sq = (long long)v * (long long)v;
            energy += sq;
        }
    }
    return energy;
}

#if (ENERGY_DETECTION_MODE == 1)
// Compute average energy over the long-term window
static long long get_longterm_average(void) {
    if (energy_hist_count == 0) return 0;
    long long sum = 0;
    for (int i = 0; i < energy_hist_count; i++) {
        sum += energy_history[i];
    }
    return sum / energy_hist_count;
}

// Compute average energy over the short-term window (most recent SHORT_TERM_WINDOW_SIZE)
static long long get_shortterm_average(void) {
    if (energy_hist_count == 0) return 0;
    int window_sz = (energy_hist_count < SHORT_TERM_WINDOW_SIZE) ? energy_hist_count : SHORT_TERM_WINDOW_SIZE;
    long long sum = 0;
    for (int i = 0; i < window_sz; i++) {
        int idx = (energy_hist_idx - 1 - i + LONG_TERM_WINDOW_SIZE) % LONG_TERM_WINDOW_SIZE;
        sum += energy_history[idx];
    }
    return sum / window_sz;
}

// Check if current energy indicates an abnormal event
static int check_adaptive_threshold(long long current_energy) {
    // Evaluate first (using OLD history)
    long long long_avg = get_longterm_average();
    long long short_avg = get_shortterm_average();
    float ratio = (long_avg > 0) ? (float)short_avg / (float)long_avg : 0.0f;
    int send = (current_energy >= ENERGY_MIN_ABSOLUTE) && (ratio > ENERGY_RATIO_THRESHOLD);
    
    // Only update history with non-detected packets (don't contaminate baseline with events)
    if (!send) {
        energy_history[energy_hist_idx] = current_energy;
        energy_hist_idx = (energy_hist_idx + 1) % LONG_TERM_WINDOW_SIZE;
        if (energy_hist_count < LONG_TERM_WINDOW_SIZE) {
            energy_hist_count++;
        }
    } else {
        DEBUG_PRINT("[Baseline] Event detected - excluding from long-term average\r\n");
    }
    
    if (energy_hist_count < SHORT_TERM_WINDOW_SIZE) {
        DEBUG_PRINT("[Warmup] E_curr: %ld | E_min: %ld | (count: %d/%d)\r\n",
                    (long)current_energy, (long)ENERGY_MIN_ABSOLUTE, energy_hist_count, SHORT_TERM_WINDOW_SIZE);
    } else {
        DEBUG_PRINT("[Adaptive] E_curr: %ld | L_avg: %ld | S_avg: %ld | Ratio: %.3f (thresh: %.1f) | Min_abs: %ld | %s\r\n",
                     (long)current_energy, (long)long_avg, (long)short_avg, ratio, ENERGY_RATIO_THRESHOLD,
                     (long)ENERGY_MIN_ABSOLUTE, send ? "*** SEND ***" : "skip"); 
    }
    
    return send;

}
#endif

static void encode_packet(uint8_t *packet, uint32_t* packet_cnt) {
	// BE encoding of each mel coef
	for (size_t i=0; i<N_MELVECS; i++) {
		for (size_t j=0; j<MELVEC_LENGTH; j++) {
			(packet+PACKET_HEADER_LENGTH)[(i*MELVEC_LENGTH+j)*2]   = mel_vectors[i][j] >> 8;
			(packet+PACKET_HEADER_LENGTH)[(i*MELVEC_LENGTH+j)*2+1] = mel_vectors[i][j] & 0xFF;
		}
	}
	// Write header and tag into the packet.
	make_packet(packet, PAYLOAD_LENGTH, 0, *packet_cnt);
	*packet_cnt += 1;
	if (*packet_cnt == 0) {
		// Should not happen as packet_cnt is 32-bit and we send at most 1 packet per second.
		DEBUG_PRINT("Packet counter overflow.\r\n");
		Error_Handler();
	}
}

static void send_spectrogram() {
	uint8_t packet[PACKET_LENGTH];

	start_cycle_count();
	encode_packet(packet, &packet_cnt);
	stop_cycle_count("Encode packet");

	start_cycle_count();
	S2LP_Send(packet, PACKET_LENGTH);
	stop_cycle_count("Send packet");

	print_encoded_packet(packet);
}

static void ADC_Callback(int buf_cplt) {
	if (rem_n_bufs != -1) {
		rem_n_bufs--;
	}
	if (rem_n_bufs == 0) {
		StopADCAcq();
	} else if (ADCDataRdy[1-buf_cplt]) {
		DEBUG_PRINT("Error: ADC Data buffer full\r\n");
		Error_Handler();
	}
	ADCDataRdy[buf_cplt] = 1;
	//start_cycle_count();
	Spectrogram_Format((q15_t *)ADCData[buf_cplt]);
	Spectrogram_Compute((q15_t *)ADCData[buf_cplt], mel_vectors[cur_melvec]);
	cur_melvec++;
	//stop_cycle_count("spectrogram");
	ADCDataRdy[buf_cplt] = 0;

	if (rem_n_bufs == 0) {
		print_spectrogram();
		
		long long energy = compute_mel_energy();
		DEBUG_PRINT("[Energy] Total: %ld\r\n", (long)energy);
		
	#if (ENERGY_DETECTION_MODE == 0)
			// Fixed threshold mode
			DEBUG_PRINT("[Detection] Energy: %ld threshold: %lld\r\n", (long)energy, (long long)ENERGY_THRESHOLD_RAW);
			if (energy >= ENERGY_THRESHOLD_RAW) {
				send_spectrogram();
			} else {
				DEBUG_PRINT("[Detection] REJECTED - Energy below fixed threshold\r\n");
			}
	#elif (ENERGY_DETECTION_MODE == 1)
			// Adaptive threshold mode: long-term baseline + short-term spike detection
			if (check_adaptive_threshold(energy)) {
				send_spectrogram();
			} else {
				DEBUG_PRINT("[Detection] REJECTED - Energy below adaptive threshold\r\n");
			}
	#else
			// No detection: always send
			send_spectrogram();
	#endif
	}
}

void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
	ADC_Callback(1);
}

void HAL_ADC_ConvHalfCpltCallback(ADC_HandleTypeDef *hadc)
{
	ADC_Callback(0);
}
