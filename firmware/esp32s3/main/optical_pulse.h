#ifndef OPTICAL_PULSE_H
#define OPTICAL_PULSE_H

#include <stdint.h>
#include "driver/gpio.h"

#ifdef __cplusplus
extern "C" {
#endif

// Zero-Risk Optical Pulse Reader configuration
#define OPTICAL_PULSE_GPIO_PIN  GPIO_NUM_4
#define DEFAULT_IMP_PER_KWH     1000

typedef struct {
    uint32_t total_pulse_count;
    uint32_t imp_per_kwh;
    float    active_power_w;
    uint64_t last_pulse_timestamp_us;
} optical_pulse_meter_t;

/**
 * @brief Initialize GPIO interrupt for the Zero-Risk Optical Pulse Meter Reader.
 * Attaches to utility meter imp/kWh flashing LED.
 */
void optical_pulse_init(gpio_num_t pin, uint32_t imp_per_kwh);

/**
 * @brief Read accumulated pulse meter status and calculated active household power.
 */
void optical_pulse_get_status(optical_pulse_meter_t *out_meter);

#ifdef __cplusplus
}
#endif

#endif // OPTICAL_PULSE_H
