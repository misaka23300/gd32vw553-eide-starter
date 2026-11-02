/*!
    \file    wifi_link.c
    \brief   Wi-Fi 链路抽象层：前端状态机 + 弱符号后端

    当前 SDK 没有 Wi-Fi 协议栈，后端全部落到弱符号空实现，wifi_link_available() 返回 0。
    接入 MSDK 后，新增一个定义同名 wifi_backend_xxx() 的 .c 文件并加入 Makefile 的
    APP_SRCS，链接时就会自动覆盖这里的弱符号，前端无需修改。
*/

#include "wifi_link.h"
#include <string.h>

/* ---------------- 弱符号后端（缺省：协议栈不存在） ---------------- */

__attribute__((weak)) int wifi_backend_init(void)
{
    return -1;
}

__attribute__((weak)) int wifi_backend_join(const char *ssid, const char *psk)
{
    (void)ssid;
    (void)psk;
    return -1;
}

__attribute__((weak)) void wifi_backend_leave(void)
{
}

__attribute__((weak)) void wifi_backend_poll(void)
{
}

__attribute__((weak)) wifi_state_t wifi_backend_state(void)
{
    return WIFI_STATE_UNAVAILABLE;
}

__attribute__((weak)) const char *wifi_backend_ip(void)
{
    return "0.0.0.0";
}

/* ---------------- 前端 ---------------- */

static wifi_state_t s_state   = WIFI_STATE_UNAVAILABLE;
static int          s_ready   = 0;
static char         s_ssid[33] = {0};

int wifi_link_init(void)
{
    if(wifi_backend_init() == 0) {
        s_ready = 1;
        s_state = WIFI_STATE_OFF;
    } else {
        s_ready = 0;
        s_state = WIFI_STATE_UNAVAILABLE;
    }
    return s_ready;
}

int wifi_link_join(const char *ssid, const char *psk)
{
    size_t n;

    if(!s_ready) {
        return -2;                       /* 没有协议栈 */
    }
    if(ssid == NULL || ssid[0] == '\0') {
        return -1;
    }

    n = strlen(ssid);
    if(n > sizeof(s_ssid) - 1U) {
        n = sizeof(s_ssid) - 1U;
    }
    memcpy(s_ssid, ssid, n);
    s_ssid[n] = '\0';

    if(wifi_backend_join(ssid, (psk != NULL) ? psk : "") != 0) {
        s_state = WIFI_STATE_ERROR;
        return -3;
    }

    s_state = WIFI_STATE_CONNECTING;
    return 0;
}

void wifi_link_leave(void)
{
    if(!s_ready) {
        return;
    }
    wifi_backend_leave();
    s_state = WIFI_STATE_OFF;
}

void wifi_link_poll(void)
{
    if(!s_ready) {
        return;
    }
    wifi_backend_poll();
    s_state = wifi_backend_state();
}

wifi_state_t wifi_link_state(void)
{
    return s_state;
}

const char *wifi_link_state_str(void)
{
    switch(s_state) {
    case WIFI_STATE_OFF:
        return "off";
    case WIFI_STATE_CONNECTING:
        return "connecting";
    case WIFI_STATE_CONNECTED:
        return "connected";
    case WIFI_STATE_ERROR:
        return "error";
    case WIFI_STATE_UNAVAILABLE:
    default:
        return "unavailable";
    }
}

const char *wifi_link_ip(void)
{
    if(s_state != WIFI_STATE_CONNECTED) {
        return "-";
    }
    return wifi_backend_ip();
}

int wifi_link_available(void)
{
    return s_ready;
}
