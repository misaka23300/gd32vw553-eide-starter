/*!
    \file    led.c
    \brief   板载 LED1（PC13）驱动，支持非阻塞闪烁

    硬件：立创 GD32VW553 开发板 LED1 = PC13，高电平点亮
          （见 wiki：库函数点亮LED灯 —— 往 PC13 输出高电平即点亮）。
          如果你的板子极性相反，把 board.h 里 LED_ACTIVE_HIGH 改成 0。
*/

#include "led.h"
#include "board.h"

#define LED_PERIOD_MIN      (50U)
#define LED_PERIOD_MAX      (60000U)
#define LED_PERIOD_DEFAULT  (2000U)

static uint8_t  s_on;                        /* 当前逻辑状态 */
static uint8_t  s_blink;                     /* 是否在闪烁 */
static uint32_t s_period = LED_PERIOD_DEFAULT;
static uint32_t s_acc;                       /* 毫秒累加 */

static void led_write(uint8_t on)
{
#if (LED_ACTIVE_HIGH != 0)
    if (on) {
        gpio_bit_set(LED_PORT, LED_PIN);
    } else {
        gpio_bit_reset(LED_PORT, LED_PIN);
    }
#else
    if (on) {
        gpio_bit_reset(LED_PORT, LED_PIN);
    } else {
        gpio_bit_set(LED_PORT, LED_PIN);
    }
#endif
}

void led_init(void)
{
    rcu_periph_clock_enable(LED_CLK);
    gpio_mode_set(LED_PORT, GPIO_MODE_OUTPUT, GPIO_PUPD_NONE, LED_PIN);
    gpio_output_options_set(LED_PORT, GPIO_OTYPE_PP, GPIO_OSPEED_25MHZ, LED_PIN);

    s_on = 0U;
    s_blink = 0U;
    s_period = LED_PERIOD_DEFAULT;
    s_acc = 0U;
    led_write(0U);
}

void led_set(uint8_t on)
{
    s_blink = 0U;               /* 手动控制优先，停掉闪烁 */
    s_on = (on != 0U) ? 1U : 0U;
    led_write(s_on);
}

void led_toggle(void)
{
    s_blink = 0U;
    s_on = (uint8_t)(s_on ? 0U : 1U);
    led_write(s_on);
}

uint8_t led_get(void)
{
    return s_on;
}

void led_blink_start(uint32_t period_ms)
{
    if (period_ms == 0U) {
        led_blink_stop();
        return;
    }
    if (period_ms < LED_PERIOD_MIN) {
        period_ms = LED_PERIOD_MIN;
    }
    if (period_ms > LED_PERIOD_MAX) {
        period_ms = LED_PERIOD_MAX;
    }

    s_period = period_ms;
    s_acc = 0U;
    s_blink = 1U;
}

void led_blink_stop(void)
{
    s_blink = 0U;
    s_acc = 0U;
}

uint8_t led_blink_active(void)
{
    return s_blink;
}

uint32_t led_blink_period(void)
{
    return s_period;
}

void led_tick(void)
{
    if (s_blink == 0U) {
        return;
    }

    s_acc++;
    if (s_acc >= s_period) {
        s_acc = 0U;
        s_on = (uint8_t)(s_on ? 0U : 1U);
        led_write(s_on);
    }
}
