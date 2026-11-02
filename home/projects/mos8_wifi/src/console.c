/*!
    \file    console.c
    \brief   USART0 命令行控制台

    命令一览：
      help                         打印帮助
      status                       打印 8 路状态 + Wi-Fi 状态
      on <1-8|all>                 打开某路 / 全部
      off <1-8|all>                关闭某路 / 全部
      toggle <1-8|all>             翻转某路 / 全部
      mask <0x00-0xFF>             按位图一次设置 8 路
      wifi                         查看 Wi-Fi 链路状态
      wifi join <ssid> <password>  连接 AP（需要协议栈后端）
      wifi leave                   断开
      ver                          版本信息
*/

#include "console.h"
#include "gd32vw55x.h"
#include "board.h"
#include "mosfet.h"
#include "wifi_link.h"
#include "led.h"

#include <stdio.h>
#include <string.h>

#define RX_RING_SIZE    (128U)
#define RX_RING_MASK    (RX_RING_SIZE - 1U)
#define LINE_MAX        (80U)
#define TOKEN_MAX       (5U)
#define CH_ALL          (0xFFU)

/* ---------------- 接收环形缓冲（中断写 / 主循环读） ---------------- */

static volatile uint8_t s_ring[RX_RING_SIZE];
static volatile uint8_t s_head;
static volatile uint8_t s_tail;

static char    s_line[LINE_MAX];
static uint8_t s_len;

void console_rx_isr(uint8_t c)
{
    uint8_t next = (uint8_t)((s_head + 1U) & RX_RING_MASK);

    if(next != s_tail) {                 /* 满了就丢新字节，不覆盖旧数据 */
        s_ring[s_head] = c;
        s_head = next;
    }
}

static int ring_pop(uint8_t *c)
{
    if(s_tail == s_head) {
        return 0;
    }
    *c = s_ring[s_tail];
    s_tail = (uint8_t)((s_tail + 1U) & RX_RING_MASK);
    return 1;
}

/* ---------------- 命令实现 ---------------- */

static void print_help(void)
{
    printf("\r\n");
    printf("  help                        this text\r\n");
    printf("  status                      channel states + wifi state\r\n");
    printf("  on   <1-8|all>              switch channel(s) on\r\n");
    printf("  off  <1-8|all>              switch channel(s) off\r\n");
    printf("  toggle <1-8|all>            toggle channel(s)\r\n");
    printf("  mask <0x00-0xFF>            set all channels by bitmap\r\n");
    printf("  led [on|off|toggle]         LED1 (PC13) steady\r\n");
    printf("  led blink [ms]              blink LED1 (default 2000ms)\r\n");
    printf("  led stop                    stop blinking\r\n");
    printf("  wifi                        show link state\r\n");
    printf("  wifi join <ssid> <password> join an access point\r\n");
    printf("  wifi leave                  disconnect\r\n");
    printf("  ver                         version info\r\n");
}

static void print_status(void)
{
    uint8_t i;
    uint8_t m = mosfet_mask();

    printf("channels:");
    for(i = 0U; i < MOS_CHANNELS; i++) {
        printf(" %u=%s", (unsigned)(i + 1U),
               ((m & (uint8_t)(1U << i)) != 0U) ? "ON" : "OFF");
    }
    printf("\r\nmask: 0x%02X\r\n", (unsigned)m);
    if(led_blink_active()) {
        printf("led: blink %ums\r\n", (unsigned)led_blink_period());
    } else {
        printf("led: %s\r\n", led_get() ? "on" : "off");
    }
    printf("wifi: %s", wifi_link_state_str());
    if(wifi_link_state() == WIFI_STATE_CONNECTED) {
        printf(" ip=%s", wifi_link_ip());
    }
    printf("\r\n");
}

/* "1".."8" -> 0..7；"all" -> CH_ALL */
static int parse_channel(const char *s, uint8_t *ch)
{
    if((strcmp(s, "all") == 0) || (strcmp(s, "ALL") == 0)) {
        *ch = CH_ALL;
        return 0;
    }
    if((s[0] >= '1') && (s[0] <= '8') && (s[1] == '\0')) {
        *ch = (uint8_t)(s[0] - '1');
        return 0;
    }
    return -1;
}

static int parse_hex8(const char *s, uint8_t *out)
{
    uint32_t v = 0U;
    uint8_t  n = 0U;

    if((s[0] == '0') && ((s[1] == 'x') || (s[1] == 'X'))) {
        s += 2;
    }
    while(*s != '\0') {
        char c = *s;
        uint8_t d;

        if((c >= '0') && (c <= '9')) {
            d = (uint8_t)(c - '0');
        } else if((c >= 'a') && (c <= 'f')) {
            d = (uint8_t)(c - 'a' + 10);
        } else if((c >= 'A') && (c <= 'F')) {
            d = (uint8_t)(c - 'A' + 10);
        } else {
            return -1;
        }
        v = (v * 16U) + d;
        if(v > 0xFFU) {
            return -1;
        }
        s++;
        n++;
    }
    if(n == 0U) {
        return -1;
    }
    *out = (uint8_t)v;
    return 0;
}

static void apply_channel(const char *verb, uint8_t ch, uint8_t on)
{
    if(ch == CH_ALL) {
        mosfet_all(on);
        printf("%s: all channels %s\r\n", verb, on ? "ON" : "OFF");
    } else {
        mosfet_set(ch, on);
        printf("%s: CH%u %s\r\n", verb, (unsigned)(ch + 1U), on ? "ON" : "OFF");
    }
}

/* 十进制无符号整数（0 ~ 1000000） */
static int parse_u32(const char *s, uint32_t *out)
{
    uint32_t v = 0U;

    if(*s == '\0') {
        return -1;
    }
    while(*s != '\0') {
        if((*s < '0') || (*s > '9')) {
            return -1;
        }
        v = (v * 10U) + (uint32_t)(*s - '0');
        if(v > 1000000U) {
            return -1;
        }
        s++;
    }
    *out = v;
    return 0;
}

static void led_report(void)
{
    if(led_blink_active()) {
        printf("led: blink %ums\r\n", (unsigned)led_blink_period());
    } else {
        printf("led: %s\r\n", led_get() ? "on" : "off");
    }
}

/* ---------------- 行解析与分发 ---------------- */

static uint8_t tokenize(char *line, char **tok, uint8_t max)
{
    uint8_t n = 0U;
    char   *p = line;

    while((*p != '\0') && (n < max)) {
        while(*p == ' ') {
            p++;
        }
        if(*p == '\0') {
            break;
        }
        tok[n++] = p;
        while((*p != '\0') && (*p != ' ')) {
            p++;
        }
        if(*p != '\0') {
            *p = '\0';
            p++;
        }
    }
    return n;
}

static void exec_line(char *line)
{
    char   *tok[TOKEN_MAX];
    uint8_t n = tokenize(line, tok, TOKEN_MAX);
    uint8_t ch;

    if(n == 0U) {
        return;
    }

    if(strcmp(tok[0], "help") == 0) {
        print_help();
    } else if(strcmp(tok[0], "status") == 0) {
        print_status();
    } else if((strcmp(tok[0], "on") == 0) || (strcmp(tok[0], "off") == 0) ||
              (strcmp(tok[0], "toggle") == 0)) {
        uint8_t on = (uint8_t)(strcmp(tok[0], "on") == 0);

        if(n < 2U) {
            printf("usage: %s <1-8|all>\r\n", tok[0]);
        } else if(parse_channel(tok[1], &ch) != 0) {
            printf("bad channel '%s' (1-8 or all)\r\n", tok[1]);
        } else if(strcmp(tok[0], "toggle") == 0) {
            if(ch == CH_ALL) {
                mosfet_set_mask((uint8_t)~mosfet_mask());
                printf("toggle: all channels toggled\r\n");
            } else {
                mosfet_toggle(ch);
                printf("toggle: CH%u -> %s\r\n", (unsigned)(ch + 1U),
                       mosfet_get(ch) ? "ON" : "OFF");
            }
        } else {
            apply_channel(tok[0], ch, on);
        }
    } else if(strcmp(tok[0], "mask") == 0) {
        uint8_t m;

        if(n < 2U) {
            printf("usage: mask <0x00-0xFF>\r\n");
        } else if(parse_hex8(tok[1], &m) != 0) {
            printf("bad mask '%s'\r\n", tok[1]);
        } else {
            mosfet_set_mask(m);
            printf("mask: 0x%02X applied\r\n", (unsigned)mosfet_mask());
        }
    } else if(strcmp(tok[0], "led") == 0) {
        if((n < 2U) || (strcmp(tok[1], "status") == 0)) {
            led_report();
        } else if(strcmp(tok[1], "on") == 0) {
            led_set(1U);
            printf("led: on\r\n");
        } else if(strcmp(tok[1], "off") == 0) {
            led_set(0U);
            printf("led: off\r\n");
        } else if(strcmp(tok[1], "toggle") == 0) {
            led_toggle();
            printf("led: %s\r\n", led_get() ? "on" : "off");
        } else if(strcmp(tok[1], "blink") == 0) {
            uint32_t ms = 2000U;

            if(n >= 3U) {
                if(parse_u32(tok[2], &ms) != 0) {
                    printf("bad period '%s' (50-60000 ms)\r\n", tok[2]);
                    return;
                }
            }
            led_blink_start(ms);
            printf("led: blink %ums\r\n", (unsigned)led_blink_period());
        } else if(strcmp(tok[1], "stop") == 0) {
            led_blink_stop();
            printf("led: stop, %s\r\n", led_get() ? "left on" : "left off");
        } else {
            printf("usage: led [on|off|toggle|blink [ms]|stop]\r\n");
        }
    } else if(strcmp(tok[0], "wifi") == 0) {
        if((n >= 2U) && (strcmp(tok[1], "join") == 0)) {
            int rc;

            if(n < 4U) {
                printf("usage: wifi join <ssid> <password>\r\n");
            } else if(!wifi_link_available()) {
                printf("wifi: no protocol stack linked in this build\r\n");
                printf("      (needs GD32VW55x_RELEASE/MSDK, see README)\r\n");
            } else {
                rc = wifi_link_join(tok[2], tok[3]);
                if(rc == 0) {
                    printf("wifi: joining '%s' ...\r\n", tok[2]);
                } else {
                    printf("wifi: join failed (rc=%d)\r\n", rc);
                }
            }
        } else if((n >= 2U) && (strcmp(tok[1], "leave") == 0)) {
            wifi_link_leave();
            printf("wifi: disconnected\r\n");
        } else {
            printf("wifi: %s", wifi_link_state_str());
            if(wifi_link_state() == WIFI_STATE_CONNECTED) {
                printf(" ip=%s", wifi_link_ip());
            }
            printf("\r\n");
        }
    } else if(strcmp(tok[0], "ver") == 0) {
        printf("mos8_wifi %s %s\r\n", __DATE__, __TIME__);
    } else {
        printf("unknown command '%s', type 'help'\r\n", tok[0]);
    }
}

/* ---------------- 对外接口 ---------------- */

void app_run_command(char *line)
{
    exec_line(line);
}

void console_init(void)
{
    s_head = 0U;
    s_tail = 0U;
    s_len  = 0U;

    usart_interrupt_enable(USART0, USART_INT_RBNE);
    eclic_irq_enable(USART0_IRQn, 1, 0);
}

void console_poll(void)
{
    uint8_t c;

    while(ring_pop(&c)) {
        if((c == '\r') || (c == '\n')) {
            printf("\r\n");
            if(s_len > 0U) {
                s_line[s_len] = '\0';
                app_run_command(s_line);
                s_len = 0U;
            }
            printf("> ");
        } else if((c == 8U) || (c == 127U)) {          /* backspace / DEL */
            if(s_len > 0U) {
                s_len--;
                printf("\b \b");
            }
        } else if((c >= 32U) && (c < 127U)) {
            if(s_len < (LINE_MAX - 1U)) {
                s_line[s_len++] = (char)c;
                putchar((int)c);
            }
        }
    }
}
