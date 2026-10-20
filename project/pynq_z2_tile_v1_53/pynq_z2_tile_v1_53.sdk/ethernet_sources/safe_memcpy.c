/* The linked newlib memcpy uses VFP registers, but this standalone BSP's
 * IRQHandler saves only integer registers (verified in the final ELF).
 * A long VFP copy can be interrupted by another library copy in the IRQ path.
 * Provide a general integer-only memcpy for this application, retaining IRQs.
 * Overlap remains undefined, exactly as for standard memcpy. */
#include <stddef.h>
#include <stdint.h>
void *memcpy(void *restrict destination,const void *restrict source,size_t bytes){
 unsigned char *d=(unsigned char*)destination;
 const unsigned char *s=(const unsigned char*)source;
#ifdef __arm__
 if((((uintptr_t)d|(uintptr_t)s)&3u)==0){
  while(bytes>=32){
   __asm__ volatile("ldmia %0!, {r2-r9}\n\tstmia %1!, {r2-r9}"
      : "+r"(s),"+r"(d) : : "r2","r3","r4","r5","r6","r7","r8","r9","memory");
   bytes-=32;
  }
 }
#endif
 /* Volatile byte accesses prevent a compiler from folding this tail into a
  * recursive call to memcpy. They also handle every unaligned buffer. */
 while(bytes--)*(volatile unsigned char*)d++=*(const volatile unsigned char*)s++;
 return destination;
}
