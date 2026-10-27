/* SPDX-License-Identifier: MIT; explicit profile upload allowlist. */
#ifndef TILELAB_PROFILE_ALLOWLIST_H
#define TILELAB_PROFILE_ALLOWLIST_H
static int profile_crc_allowed(uint32_t crc) { return crc==2781797194u || crc==2384441772u; }
extern uint32_t tilelab_phy_retry_count;
static uint32_t profile_status[8]={0x2000c001u,2u,2781797194u,2384441772u,MODEL_BYTES,MODEL_GRID,47u,0u};
#endif
