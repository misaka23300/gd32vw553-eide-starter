/*!
    \file    board.c
    \brief  8 路 MOS 管引脚表 + LED 初始化
*/

#include "board.h"

/*
 * 通道引脚表：g_mos_pins[0] 对应命令里的通道 1，以此类推。
 *
 * 默认用 PA0 ~ PA7（PA8 是 USART0_RX，PB15 是 USART0_TX，PC13 是 LED）。
 * 如果你的板子上这些脚被别的外设占用，直接改下面的表即可，例如：
 *     {GPIOB, GPIO_PIN_0, RCU_GPIOB},
 */
const mos_pin_t g_mos_pins[MOS_CHANNELS] = {
    {GPIOA, GPIO_PIN_0, RCU_GPIOA},   /* CH1 */
    {GPIOA, GPIO_PIN_1, RCU_GPIOA},   /* CH2 */
    {GPIOA, GPIO_PIN_2, RCU_GPIOA},   /* CH3 */
    {GPIOA, GPIO_PIN_3, RCU_GPIOA},   /* CH4 */
    {GPIOA, GPIO_PIN_4, RCU_GPIOA},   /* CH5 */
    {GPIOA, GPIO_PIN_5, RCU_GPIOA},   /* CH6 */
    {GPIOA, GPIO_PIN_6, RCU_GPIOA},   /* CH7 */
    {GPIOA, GPIO_PIN_7, RCU_GPIOA},   /* CH8 */
};

