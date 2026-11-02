/*!
    \file    gd32vw55x_it.c
    \brief   中断服务程序
*/

#include "gd32vw55x_it.h"
#include "gd32vw55x.h"
#include "systick.h"
#include "console.h"

/* 1ms 系统节拍 */
void eclic_mtip_handler(void)
{
    ECLIC_ClearPendingIRQ(CLIC_INT_TMR);
    delay_decrement();
}

/* USART0 接收中断：把字节交给控制台缓冲 */
void USART0_IRQHandler(void)
{
    if(RESET != usart_flag_get(USART0, USART_FLAG_RBNE)) {
        console_rx_isr((uint8_t)usart_data_receive(USART0));
    }
}
