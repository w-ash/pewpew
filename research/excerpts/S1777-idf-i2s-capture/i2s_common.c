// Excerpt: components/esp_driver_i2s/i2s_common.c lines 940-948, verbatim, at the pin in LICENSE-NOTE.md.
    if (handle->callbacks.on_recv) {
        user_need_yield |= handle->callbacks.on_recv(handle, &evt, handle->user_data);
    }
    if (xQueueIsQueueFullFromISR(handle->msg_queue)) {
        xQueueReceiveFromISR(handle->msg_queue, &dummy, &need_yield1);
        if (handle->callbacks.on_recv_q_ovf) {
            user_need_yield |= handle->callbacks.on_recv_q_ovf(handle, &evt, handle->user_data);
        }
    }
// Excerpt: components/esp_driver_i2s/i2s_common.c lines 1963-1995, verbatim, at the pin in LICENSE-NOTE.md.
#endif
    /* Calculate the new divider */
    hal_utils_clk_div_t mclk_div = {};
    i2s_hal_calc_mclk_precise_division(new_sclk_hz, new_mclk, &mclk_div);
    /* mclk_div = sclk / mclk >= 2 */
    if (mclk_div.integer < 2) {
        ret = ESP_ERR_INVALID_ARG;
        goto err;
    }
    /* Set the new divider for MCLK */
    PERIPH_RCC_ATOMIC() {
        if (handle->dir == I2S_DIR_TX) {
            i2s_ll_tx_set_mclk(handle->controller->hal.dev, &mclk_div);
#if SOC_I2S_HW_VERSION_2
            i2s_ll_tx_update(handle->controller->hal.dev);
#endif
        } else {
            i2s_ll_rx_set_mclk(handle->controller->hal.dev, &mclk_div);
#if SOC_I2S_HW_VERSION_2
            i2s_ll_rx_update(handle->controller->hal.dev);
#endif
        }
    }
    /* Save the current mclk frequency */
    handle->sclk_hz = new_sclk_hz;
#if SOC_I2S_SUPPORTS_APLL
    if (handle->clk_src == I2S_CLK_SRC_APLL) {
        i2s_apll_operation_finish(handle, &apll_operation, true);
    }
#endif
    handle->curr_mclk_hz = (uint32_t)(((uint64_t)new_sclk_hz * mclk_div.denominator) /
                                      (mclk_div.integer * mclk_div.denominator + mclk_div.numerator));
result:
