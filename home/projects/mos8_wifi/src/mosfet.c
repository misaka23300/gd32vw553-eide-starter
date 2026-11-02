/*!
    \file    mosfet.c
    \brief   8 路 MOS 管输出驱动实现
*/

#include "mosfet.h"
#include "board.h"

/* bit0 = CH1 ... bit7 = CH8，逻辑状态（1 = 导通） */
static uint8_t s_state = 0U;

static void pin_write(uint8_t ch, uint8_t on)
{
    const mos_pin_t *p = &g_mos_pins[ch];

#if (MOS_ACTIVE_HIGH != 0)
    if(on) {
        gpio_bit_set(p->port, p->pin);      /* 高电平导通 */
    } else {
        gpio_bit_reset(p->port, p->pin);
    }
#else
    if(on) {
        gpio_bit_reset(p->port, p->pin);    /* 低电平导通 */
    } else {
        gpio_bit_set(p->port, p->pin);
    }
#endif
}

void mosfet_init(void)
{
    uint8_t i;

    for(i = 0U; i < MOS_CHANNELS; i++) {
        rcu_periph_clock_enable(g_mos_pins[i].rcu);
        gpio_mode_set(g_mos_pins[i].port, GPIO_MODE_OUTPUT, GPIO_PUPD_NONE,
                      g_mos_pins[i].pin);
        gpio_output_options_set(g_mos_pins[i].port, GPIO_OTYPE_PP,
                                GPIO_OSPEED_25MHZ, g_mos_pins[i].pin);
        pin_write(i, 0U);                   /* 上电先全部关闭，避免误动作 */
    }
    s_state = 0U;
}

void mosfet_set(uint8_t ch, uint8_t on)
{
    if(ch >= MOS_CHANNELS) {
        return;
    }

    if(on) {
        s_state |= (uint8_t)(1U << ch);
    } else {
        s_state &= (uint8_t)~(1U << ch);
    }
    pin_write(ch, on);
}

void mosfet_toggle(uint8_t ch)
{
    if(ch >= MOS_CHANNELS) {
        return;
    }
    mosfet_set(ch, (uint8_t)((s_state & (1U << ch)) ? 0U : 1U));
}

void mosfet_all(uint8_t on)
{
    uint8_t i;

    for(i = 0U; i < MOS_CHANNELS; i++) {
        mosfet_set(i, on);
    }
}

uint8_t mosfet_get(uint8_t ch)
{
    if(ch >= MOS_CHANNELS) {
        return 0U;
    }
    return (uint8_t)((s_state & (1U << ch)) ? 1U : 0U);
}

uint8_t mosfet_mask(void)
{
    return s_state;
}

void mosfet_set_mask(uint8_t mask)
{
    uint8_t i;

    for(i = 0U; i < MOS_CHANNELS; i++) {
        mosfet_set(i, (uint8_t)((mask & (1U << i)) ? 1U : 0U));
    }
}
