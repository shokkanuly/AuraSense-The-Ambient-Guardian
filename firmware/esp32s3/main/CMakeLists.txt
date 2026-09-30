idf_component_register(SRCS "main.c" "optical_pulse.c"
                    INCLUDE_DIRS "."
                    REQUIRES driver esp_timer esp_ringbuf)
