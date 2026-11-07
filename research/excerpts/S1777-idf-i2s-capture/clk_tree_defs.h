// Excerpt: components/soc/esp32s3/include/soc/clk_tree_defs.h lines 325-341, verbatim, at the pin in LICENSE-NOTE.md.
 * @brief Array initializer for all supported clock sources of I2S
 */
#define SOC_I2S_CLKS {SOC_MOD_CLK_PLL_F240M, SOC_MOD_CLK_PLL_F160M, SOC_MOD_CLK_XTAL, I2S_CLK_SRC_EXTERNAL}

/**
 * @brief I2S clock source enum
 */
typedef enum {
    I2S_CLK_SRC_DEFAULT = SOC_MOD_CLK_PLL_F160M,                    /*!< Select PLL_F160M as the default source clock  */
    I2S_CLK_SRC_PLL_240M = SOC_MOD_CLK_PLL_D2,                      /*!< Select PLL_D2 as the source clock.
                                                                         It is default to 240MHz while PLL is 480MHz,
                                                                         but it will be 160MHz if PLL is 320MHz */
    I2S_CLK_SRC_PLL_160M = SOC_MOD_CLK_PLL_F160M,                   /*!< Select PLL_F160M as the source clock */
    I2S_CLK_SRC_XTAL = SOC_MOD_CLK_XTAL,                            /*!< Select XTAL as the source clock */
    I2S_CLK_SRC_EXTERNAL = -1,                                      /*!< Select external clock as source clock */
} soc_periph_i2s_clk_src_t;

