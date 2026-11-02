/*!
    \file    main.c
    \brief   GD32VW553 8 路 MOS 管控制器

    上电后：
      1. 8 路 GPIO 全部初始化为输出并保持关闭
      2. 打开 USART0 命令行（115200 8N1，TX=PB15 / RX=PA8）
      3. 初始化 Wi-Fi 链路层（当前 SDK 无协议栈时为 unavailable 状态）
      4. LED1（PC13）默认 2 秒（2000ms）闪烁做心跳
      5. 主循环：处理串口命令、轮询 Wi-Fi 链路、驱动 LED 闪烁
*/

#include "gd32vw55x.h"
#include "systick.h"
#include "board.h"
#include "mosfet.h"
#include "console.h"
#include "wifi_link.h"
#include "led.h"

#include <stdio.h>

/* 在 retarget.c 中实现 */
extern void uart_init(uint32_t baudrate);

int main(void)
{
    systick_config();
    uart_init(115200U);

    led_init();
    mosfet_init();
    console_init();

    printf("\r\n========================================\r\n");
    printf(" GD32VW553  8-channel MOSFET controller\r\n");
    printf(" %s %s   CK_SYS=%u Hz\r\n", __DATE__, __TIME__,
           (unsigned int)rcu_clock_freq_get(CK_SYS));
    printf("========================================\r\n");

    if(wifi_link_init() == 0) {
        printf("wifi : protocol stack ready\r\n");
    } else {
        printf("wifi : no protocol stack linked (local console only)\r\n");
    }

    led_blink_start(2000U);         /* 心跳：2 秒一个亮灭周期 */
    printf("led  : blink 2000ms (heartbeat)\r\n");
    printf("type 'help' for commands\r\n> ");

    while(1) {
        console_poll();
        wifi_link_poll();

        delay_1ms(1U);

        led_tick();
    }
}
