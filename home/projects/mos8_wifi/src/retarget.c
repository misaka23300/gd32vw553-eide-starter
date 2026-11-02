/*!
    \file    retarget.c
    \brief   USART0 console retarget for printf (TX PB15 / RX PA8, AF8, 115200 8N1)
*/

#include "gd32vw55x.h"
#include <stddef.h>

void uart_init(uint32_t baudrate)
{
    rcu_periph_clock_enable(RCU_GPIOB);
    rcu_periph_clock_enable(RCU_GPIOA);
    rcu_periph_clock_enable(RCU_USART0);

    gpio_af_set(GPIOB, GPIO_AF_8, GPIO_PIN_15);
    gpio_mode_set(GPIOB, GPIO_MODE_AF, GPIO_PUPD_PULLUP, GPIO_PIN_15);
    gpio_output_options_set(GPIOB, GPIO_OTYPE_PP, GPIO_OSPEED_25MHZ, GPIO_PIN_15);

    gpio_af_set(GPIOA, GPIO_AF_2, GPIO_PIN_8);
    gpio_mode_set(GPIOA, GPIO_MODE_AF, GPIO_PUPD_PULLUP, GPIO_PIN_8);
    gpio_output_options_set(GPIOA, GPIO_OTYPE_PP, GPIO_OSPEED_25MHZ, GPIO_PIN_8);

    usart_deinit(USART0);
    usart_baudrate_set(USART0, baudrate);
    usart_receive_config(USART0, USART_RECEIVE_ENABLE);
    usart_transmit_config(USART0, USART_TRANSMIT_ENABLE);
    usart_enable(USART0);
}

int _write(int fd, const void *ptr, size_t len)
{
    const uint8_t *p = (const uint8_t *)ptr;
    size_t i;

    (void)fd;
    for(i = 0U; i < len; i++) {
        usart_data_transmit(USART0, p[i]);
        while(usart_flag_get(USART0, USART_FLAG_TBE) == RESET) {
        }
    }
    return (int)len;
}
