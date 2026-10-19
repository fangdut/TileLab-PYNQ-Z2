#include <stdint.h>
#include <stddef.h>
#ifdef _WIN32
#define TILE_EXPORT __declspec(dllexport)
#else
#define TILE_EXPORT
#endif
/* Offline reference only. No live workstation/ARM dependency on this library. */
TILE_EXPORT void tile_boost_predict(const uint8_t *x, size_t n,
    const int16_t *feature, const uint8_t *threshold,
    const int32_t *left, const int32_t *right, const int32_t *value,
    const int32_t *roots, int tree_count, int32_t baseline, int32_t *out) {
    size_t p;
    for (p=0;p<n;++p) {
        const uint8_t *row=x+14*p;
        int64_t sum=baseline;
        int t;
        for (t=0;t<tree_count;++t) {
            int32_t node=roots[t];
            while (feature[node]>=0)
                node=row[feature[node]]<=threshold[node]?left[node]:right[node];
            sum+=value[node];
        }
        out[p]=(int32_t)sum;
    }
}
