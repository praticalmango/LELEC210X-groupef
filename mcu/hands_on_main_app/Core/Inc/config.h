/*
 * config.h
 */

#ifndef INC_CONFIG_H_
#define INC_CONFIG_H_

#include <stdio.h>

// Runtime parameters
#define MAIN_APP 0
#define EVAL_RADIO 1

#define RUN_CONFIG EVAL_RADIO

// Radio parameters
#define ENABLE_RADIO 1

// General UART enable/disable (disable for low-power operation)
#define ENABLE_UART 0

// In continuous mode, we start and stop continuous acquisition on button press.
// In non-continuous mode, we send a single packet on button press.
#define CONTINUOUS_ACQ 1

// Spectrogram parameters
#define SAMPLES_PER_MELVEC 512
#define MELVEC_LENGTH 20
#define N_MELVECS 20

// Energy-based event detection (before sending a packet)
// Mode selection: 0 = fixed threshold, 1 = adaptive threshold (long/short term ratio)
#define ENERGY_DETECTION_MODE 1

// --- Fixed threshold mode (ENERGY_DETECTION_MODE == 0) ---
#define ENERGY_THRESHOLD_RAW (100000000LL)

// --- Adaptive threshold mode (ENERGY_DETECTION_MODE == 1) ---
// Number of packets to average for long-term baseline (e.g., last 30 packets)
#define LONG_TERM_WINDOW_SIZE 10
// Number of packets to average for short-term detection (e.g., last 3 packets)
#define SHORT_TERM_WINDOW_SIZE 2
// Multiplier: send packet when short_term_avg > k * long_term_avg
// Higher value = more conservative (fewer false positives), lower = more sensitive
#define ENERGY_RATIO_THRESHOLD 1.2f
// Minimum absolute energy to avoid false positives in silence
#define ENERGY_MIN_ABSOLUTE (500000LL)

// Enable performance measurements
#define PERF_COUNT 0

#define USE_HAMMING 0

// Enable debug print
#define DEBUGP 0

#if (DEBUGP == 1)
#define DEBUG_PRINT(...) do{ printf(__VA_ARGS__ ); } while( 0 )
#else
#define DEBUG_PRINT(...) do{ } while ( 0 )
#endif



#endif /* INC_CONFIG_H_ */
