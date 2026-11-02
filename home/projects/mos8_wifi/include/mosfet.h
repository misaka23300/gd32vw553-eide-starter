/*!
    \file    mosfet.h
    \brief   8 路 MOS 管输出驱动（GPIO 层面）
*/

#ifndef MOSFET_H
#define MOSFET_H

#include <stdint.h>

/* 初始化全部通道，输出全部关闭 */
void mosfet_init(void);

/* ch: 0 ~ MOS_CHANNELS-1；on: 0 关 / 非 0 开 */
void mosfet_set(uint8_t ch, uint8_t on);

/* 翻转单个通道 */
void mosfet_toggle(uint8_t ch);

/* 全部通道一起开关 */
void mosfet_all(uint8_t on);

/* 读取某通道当前逻辑状态（0/1） */
uint8_t mosfet_get(uint8_t ch);

/* 8 路状态位图（bit0 = CH1 ... bit7 = CH8） */
uint8_t mosfet_mask(void);

/* 按位图一次性设置全部通道 */
void mosfet_set_mask(uint8_t mask);

#endif /* MOSFET_H */
