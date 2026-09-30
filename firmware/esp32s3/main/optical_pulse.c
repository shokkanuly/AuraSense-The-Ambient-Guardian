#include "optical_pulse.h"
#include "esp_timer.h"
#include "esp_log.h"

static const char *TAG = "OPTICAL_PULSE";

static volatile optical_pulse_meter_t g_pulse_meter = {
    .total_pulse_count = 0,
    .imp_per_kwh = DEFAULT_IMP_PER_KWH,
    .active_power_w = 0.0f,
    .last_pulse_timestamp_us = 0
};

static void IRAM_ATTR gpio_pulse_isr_handler(void *arg) {
    uint64_t now_us = esp_timer_get_time();
    uint64_t diff_us = now_us - g_pulse_meter.last_pulse_timestamp_us;
    
    // Debounce noise pulses < 10ms
    if (diff_us > 10000) {
        g_pulse_meter.total_pulse_count++;
        if (g_pulse_meter.last_pulse_timestamp_us > 0 && diff_us > 0) {
            // Power (W) = (3,600,000,000 / (imp_per_kwh * dt_in_us))
            float power = (3600000000.0f / (float)(g_pulse_meter.imp_per_kwh * diff_us));
            g_pulse_meter.active_power_w = power;
        }
        g_pulse_meter.last_pulse_timestamp_us = now_us;
    }
}

void optical_pulse_init(gpio_num_t pin, uint32_t imp_per_kwh) {
    g_pulse_meter.imp_per_kwh = imp_per_kwh;
    
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << pin),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_NEGEDGE
    };
    gpio_config(&io_conf);
    
    gpio_install_isr_service(0);
    gpio_isr_handler_add(pin, gpio_pulse_isr_handler, NULL);
    ESP_LOGI(TAG, "Zero-Risk Optical Pulse Reader initialized on GPIO %d (%d imp/kWh)", pin, imp_per_kwh);
}

void optical_pulse_get_status(optical_pulse_meter_t *out_meter) {
    if (out_meter) {
        out_meter->total_pulse_count = g_pulse_meter.total_pulse_count;
        out_meter->imp_per_kwh = g_pulse_meter.imp_per_kwh;
        out_meter->active_power_w = g_pulse_meter.active_power_w;
        out_meter->last_pulse_timestamp_us = g_pulse_meter.last_pulse_timestamp_us;
    }
}
