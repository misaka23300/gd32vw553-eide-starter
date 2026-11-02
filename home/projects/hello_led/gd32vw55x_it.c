/*!
    \file    gd32vw55x_it.c
    \brief   interrupt service routines
*/

#include "gd32vw55x_it.h"
#include "gd32vw55x.h"
#include "systick.h"

void eclic_mtip_handler(void)
{
    ECLIC_ClearPendingIRQ(CLIC_INT_TMR);
    delay_decrement();
}
