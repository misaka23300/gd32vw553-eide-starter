/*!
    \file    main.c
    \brief   GD32VW553 bare-metal template: blink the on-board LED and print to USART0

    Target board: LCKFB GD32VW553-HMQ6 (LED on PC13)
*/

#include "gd32vw55x.h"
#include "systick.h"
#include <stdio.h>

#define LED_PORT    GPIOC
#define LED_PIN     GPIO_PIN_13
#define LED_CLK     RCU_GPIOC
#define LED_ON()    gpio_bit_reset(LED_PORT, LED_PIN)
#define LED_OFF()   gpio_bit_set(LED_PORT, LED_PIN)
#define LED_TOGGLE() gpio_bit_toggle(LED_PORT, LED_PIN)

void uart_init(uint32_t baudrate);

static void led_init(void)
{
    rcu_periph_clock_enable(LED_CLK);
    gpio_mode_set(LED_PORT, GPIO_MODE_OUTPUT, GPIO_PUPD_NONE, LED_PIN);
    gpio_output_options_set(LED_PORT, GPIO_OTYPE_PP, GPIO_OSPEED_25MHZ, LED_PIN);
    LED_OFF();
}

int main(void)
{
    systick_config();
    led_init();
    uart_init(115200U);

    printf("\r\nGD32VW553 hello_led start, CK_SYS=%u Hz\r\n",
           (unsigned int)rcu_clock_freq_get(CK_SYS));

    while(1) {
        LED_TOGGLE();
        printf("LED toggle\r\n");
        delay_1ms(500U);
    }
}
