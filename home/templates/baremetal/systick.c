/*!
    \file    systick.c
    \brief   1 ms tick based on the RISC-V core private timer (mtime)
*/

#include "gd32vw55x.h"
#include "systick.h"

static volatile uint32_t delay;

void systick_config(void)
{
    SysTimer_SetControlValue(SysTimer_MTIMECTL_CMPCLREN_Msk);
    SysTimer_SetCompareValue(SystemCoreClock / 4000U);
    __ECLIC_SetTrigIRQ(CLIC_INT_TMR, ECLIC_POSTIVE_EDGE_TRIGGER);
    eclic_irq_enable(CLIC_INT_TMR, 0, 0);
}

void delay_1ms(uint32_t count)
{
    delay = count;
    while(0U != delay) {
    }
}

void delay_decrement(void)
{
    if(0U != delay) {
        delay--;
    }
}
