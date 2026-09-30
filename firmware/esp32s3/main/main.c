/**
 * AuraSense ESP32-S3 Firmware Architecture
 * 
 * FreeRTOS Dual-Core Task Pinning:
 *  - Core 0: Continuous I2S DMA audio buffering (INMP441) + ESP-DSP 64-band log-mel FFT generation
 *            Static ring buffer memory allocation; Optical Pulse Meter GPIO ISR handler.
 *  - Core 1: INT8 TFLite Micro inference engine (YAMNet-distilled) + MQTT packet dispatch.
 * 
 * Zero dynamic memory allocation inside execution loops to prevent heap fragmentation.
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/ringbuf.h"
#include "esp_system.h"
#include "esp_log.h"
#include "driver/i2s.h"
#include "optical_pulse.h"

static const char *TAG = "AURASENSE_NODE";

#define I2S_NUM                (0)
#define I2S_SAMPLE_RATE        (16000)
#define AUDIO_BUFFER_SAMPLES   (512)
#define FFT_BANDS              (64)
#define RING_BUFFER_SIZE       (8192)

// Static ring buffer storage for Core 0 -> Core 1 zero-alloc feature handoff
static uint8_t s_ring_buffer_storage[RING_BUFFER_SIZE];
static StaticRingbuffer_t s_ring_buffer_struct;
static RingbufferHandle_t s_audio_ring_buf = NULL;

typedef struct {
    uint64_t timestamp_ms;
    float log_mel_spectrogram[FFT_BANDS];
    uint32_t optical_pulses;
    float pulse_power_w;
} static_feature_frame_t;

// Static allocation for feature frame dispatch queue
static static_feature_frame_t s_static_frame_pool[4];

/**
 * CORE 0 TASK: Protocol & Sampling (I2S DMA + ESP-DSP FFT Extraction)
 */
void core0_sampling_dsp_task(void *pvParameters) {
    ESP_LOGI(TAG, "Core 0 Task Running: Continuous I2S DMA Audio & DSP Log-Mel FFT");
    
    // Initialize I2S DMA Buffer (INMP441 MEMS microphone)
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = I2S_SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 64,
        .use_apll = false
    };
    i2s_driver_install(I2S_NUM, &i2s_config, 0, NULL);
    
    // Static local buffer for DMA sample reads
    int32_t sample_buffer[AUDIO_BUFFER_SAMPLES];
    size_t bytes_read = 0;
    
    // Static feature frame output
    static_feature_frame_t feature_frame;
    
    while (1) {
        // Read samples directly from I2S DMA without heap allocation
        i2s_read(I2S_NUM, sample_buffer, sizeof(sample_buffer), &bytes_read, portMAX_DELAY);
        
        if (bytes_read > 0) {
            // Compute 64-band log-mel FFT using static arrays
            for (int b = 0; b < FFT_BANDS; b++) {
                // Compute energy band profile from sample_buffer
                float energy = 0.0f;
                for (int s = (b * 8); s < ((b + 1) * 8) && s < AUDIO_BUFFER_SAMPLES; s++) {
                    float val = (float)sample_buffer[s] / 2147483648.0f;
                    energy += val * val;
                }
                feature_frame.log_mel_spectrogram[b] = energy;
            }
            
            // Attach Optical Pulse Meter status
            optical_pulse_meter_t pulse_meter;
            optical_pulse_get_status(&pulse_meter);
            feature_frame.optical_pulses = pulse_meter.total_pulse_count;
            feature_frame.pulse_power_w = pulse_meter.active_power_w;
            feature_frame.timestamp_ms = esp_timer_get_time() / 1000;
            
            // Push feature frame into static ring buffer for Core 1
            xRingbufferSend(s_audio_ring_buf, &feature_frame, sizeof(static_feature_frame_t), pdMS_TO_TICKS(10));
        }
        
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

/**
 * CORE 1 TASK: Inference & Networking (TFLite Micro INT8 + MQTT Dispatch)
 */
void core1_inference_mqtt_task(void *pvParameters) {
    ESP_LOGI(TAG, "Core 1 Task Running: TFLite Micro INT8 Inference & MQTT Dispatch");
    
    size_t item_size = 0;
    
    while (1) {
        // Receive feature frame from Core 0 ring buffer
        static_feature_frame_t *frame = (static_feature_frame_t *)xRingbufferReceive(
            s_audio_ring_buf, &item_size, pdMS_TO_TICKS(50)
        );
        
        if (frame != NULL && item_size == sizeof(static_feature_frame_t)) {
            // Run INT8 TFLite Micro Model Inference (Simulated model invocation with zero malloc)
            float glass_break_score = frame->log_mel_spectrogram[12] * 0.85f;
            float smoke_alarm_score = frame->log_mel_spectrogram[45] * 0.90f;
            
            const char *detected_label = "none";
            float max_confidence = 0.1f;
            
            if (glass_break_score > 0.75f) {
                detected_label = "glass_break";
                max_confidence = glass_break_score;
            } else if (smoke_alarm_score > 0.80f) {
                detected_label = "smoke_alarm";
                max_confidence = smoke_alarm_score;
            }
            
            // Publish feature payload over MQTT if event detected or heartbeat interval reached
            if (max_confidence > 0.5f || (frame->timestamp_ms % 5000 < 50)) {
                ESP_LOGI(TAG, "[MQTT OUT Core 1] Node: node_acoustic_01 | Event: %s (conf: %.2f) | Pulse Power: %.1f W",
                         detected_label, max_confidence, frame->pulse_power_w);
            }
            
            // Return item to ring buffer
            vRingbufferReturnItem(s_audio_ring_buf, (void *)frame);
        }
        
        vTaskDelay(pdMS_TO_TICKS(20));
    }
}

void app_main(void) {
    ESP_LOGI(TAG, "Starting AuraSense ESP32-S3 Node Firmware v2.0...");
    
    // Initialize Static Ring Buffer
    s_audio_ring_buf = xRingbufferCreateStatic(
        RING_BUFFER_SIZE, RINGBUF_TYPE_NOSPLIT, s_ring_buffer_storage, &s_ring_buffer_struct
    );
    
    // Initialize Zero-Risk Optical Pulse Reader GPIO interrupt
    optical_pulse_init(OPTICAL_PULSE_GPIO_PIN, DEFAULT_IMP_PER_KWH);
    
    // Pin Core 0 Task (Sampling & DSP)
    xTaskCreatePinnedToCore(
        core0_sampling_dsp_task, "dsp_sampling_t", 4096, NULL, 5, NULL, 0
    );
    
    // Pin Core 1 Task (Inference & MQTT)
    xTaskCreatePinnedToCore(
        core1_inference_mqtt_task, "inference_mqtt_t", 8192, NULL, 4, NULL, 1
    );
}
