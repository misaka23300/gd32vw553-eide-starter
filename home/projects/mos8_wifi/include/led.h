/*!
    \file    led.h
    \brief   板载 LED1（PC13）控制 + 非阻塞闪烁

    立创 GD32VW553 开发板：LED1 接 PC13，输出高电平点亮。

    用法：
        led_init();                 初始化（默认熄灭）
        led_set(1);                 常亮
        led_blink_start(500U);      500ms 周期闪烁（非阻塞）
        led_tick();                 主循环里每 1ms 调用一次
*/

#ifndef LED_H
#define LED_H

#include <stdint.h>

void led_init(void);

/* 手动控制：会停止闪烁 */
void led_set(uint8_t on);
void led_toggle(void);
uint8_t led_get(void);

/* 非阻塞闪烁：period_ms 为一个完整亮灭周期，0 等价于 stop */
void led_blink_start(uint32_t period_ms);
void led_blink_stop(void);
uint8_t led_blink_active(void);
uint32_t led_blink_period(void);

/* 时基：主循环每 1ms 调一次 */
void led_tick(void);

#endif /* LED_H */
