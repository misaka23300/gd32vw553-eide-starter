/*!
    \file    wifi_link.h
    \brief   Wi-Fi 链路抽象层（前后端分离）

    这个工程编译所用的 GD32VW55x_Firmware_Library 只有外设驱动，没有 Wi-Fi 协议栈。
    真正的 join AP 需要 GD32VW55x_RELEASE(MSDK) 里的 Wi-Fi 中间件，所以这里做了两层：

      wifi_link_xxx()     前端：状态机 + 对外统一接口（本文件，始终可用）
      wifi_backend_xxx()  后端：弱符号空实现；放入 wifi_backend_msdk.c 并参与编译后
                                自动覆盖，前端不用改一行代码。

    后端接口约定（实现者必须满足）：
      wifi_backend_init()        0 = 协议栈可用，其它 = 不可用
      wifi_backend_join()        0 = 已开始连接（异步），其它 = 参数/调用错误
      wifi_backend_poll()        在主循环里被反复调用，用于驱动协议栈和状态刷新
      wifi_backend_state()       返回当前链路状态，前端直接透传
      wifi_backend_ip()          连接成功后返回点分十进制 IP 字符串
*/

#ifndef WIFI_LINK_H
#define WIFI_LINK_H

#include <stdint.h>

typedef enum {
    WIFI_STATE_UNAVAILABLE = 0,   /* 没有链接协议栈 */
    WIFI_STATE_OFF,               /* 协议栈就绪，未连接 */
    WIFI_STATE_CONNECTING,        /* 正在连接 */
    WIFI_STATE_CONNECTED,         /* 已连接，拿到 IP */
    WIFI_STATE_ERROR              /* 连接失败 */
} wifi_state_t;

/* ---------- 前端 ---------- */
int         wifi_link_init(void);
int         wifi_link_join(const char *ssid, const char *psk);
void        wifi_link_leave(void);
void        wifi_link_poll(void);
wifi_state_t wifi_link_state(void);
const char *wifi_link_state_str(void);
const char *wifi_link_ip(void);
int         wifi_link_available(void);

/* ---------- 后端钩子（弱符号，可被覆盖） ---------- */
int         wifi_backend_init(void);
int         wifi_backend_join(const char *ssid, const char *psk);
void        wifi_backend_leave(void);
void        wifi_backend_poll(void);
wifi_state_t wifi_backend_state(void);
const char *wifi_backend_ip(void);

#endif /* WIFI_LINK_H */
