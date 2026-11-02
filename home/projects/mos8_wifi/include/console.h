/*!
    \file    console.h
    \brief   USART0 命令行控制台（接收走中断 + 环形缓冲）
*/

#ifndef CONSOLE_H
#define CONSOLE_H

#include <stdint.h>

/* 打开 USART0 接收中断并复位行缓冲；必须在 uart_init() 之后调用 */
void console_init(void);

/* 主循环里反复调用：取字符、回显、拼行、执行命令 */
void console_poll(void);

/* 由 USART0 中断服务程序调用，把收到的字节丢进环形缓冲 */
void console_rx_isr(uint8_t c);

/* 命令执行入口：串口和控制台共用；将来接上 TCP 服务后，
   网络层收到一整行也可以直接调用它（不打印提示符） */
void app_run_command(char *line);

#endif /* CONSOLE_H */
