/*!
    \file    board.h
    \brief   板级配置：8 路 MOS 管引脚映射 + 板载 LED

    Target board: LCKFB GD32VW553-HMQ6 (LED on PC13, USART0 TX=PB15 / RX=PA8)

    改引脚只需要动 board.c 里的表，其他代码不用改。
*/

#ifndef BOARD_H
#define BOARD_H

#include "gd32vw55x.h"

/* 通道数，必须与 board.c 里的表项数量一致 */
#define MOS_CHANNELS        (8U)

/* 驱动极性：
   1 = GPIO 输出高电平 -> MOS 管导通（低边 NMOS 经栅极电阻直驱时用这个）
   0 = GPIO 输出低电平 -> MOS 管导通（光耦 / 反相驱动 / PNP 驱动时用这个） */
#define MOS_ACTIVE_HIGH     (1)

typedef struct {
    uint32_t        port;
    uint32_t        pin;
    rcu_periph_enum rcu;
} mos_pin_t;

extern const mos_pin_t g_mos_pins[MOS_CHANNELS];

/* 板载 LED1：PC13。
   立创 GD32VW553 开发板为高电平点亮（wiki：库函数点亮LED灯）。
   若你的板子相反，把 LED_ACTIVE_HIGH 改成 0 即可。 */
#define LED_PORT        GPIOC
#define LED_PIN         GPIO_PIN_13
#define LED_CLK         RCU_GPIOC
#define LED_ACTIVE_HIGH (1)

#endif /* BOARD_H */
