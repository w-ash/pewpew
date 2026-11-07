// Excerpt: components/esp_driver_i2s/include/driver/i2s_types.h lines 64-77, verbatim, at the pin in LICENSE-NOTE.md.

/**
 * @brief Event structure used in I2S event queue
 */
typedef struct {
    void                *dma_buf;/**< The first level pointer of DMA buffer that just finished sending or receiving for `on_recv` and `on_sent` callback
                                  *  NULL for `on_recv_q_ovf` and `on_send_q_ovf` callback
                                  */
    size_t              size;   /**< The buffer size of DMA buffer when success to send or receive,
                                  *  also the buffer size that dropped when queue overflow.
                                  *  It is related to the dma_frame_num and data_bit_width, typically it is fixed when data_bit_width is not changed.
                                  */
} i2s_event_data_t;

