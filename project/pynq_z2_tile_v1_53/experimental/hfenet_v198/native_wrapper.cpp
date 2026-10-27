// Offline C-source verification entry points, never part of deployed firmware.
#include <stdint.h>
extern void texture_integer(const uint64_t*,uint64_t*,const uint32_t*,uint32_t*,unsigned,unsigned);
extern void (*hfe_observer)(unsigned,const uint64_t*,unsigned,unsigned);
extern "C" __declspec(dllexport) void tile_run(const uint64_t*m,uint64_t*w,const uint32_t*r,uint32_t*out,unsigned width,unsigned height){texture_integer(m,w,r,out,width,height);}
extern "C" __declspec(dllexport) void tile_observer(void (*fn)(unsigned,const uint64_t*,unsigned,unsigned)){hfe_observer=fn;}
