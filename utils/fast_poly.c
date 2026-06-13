#include <stdint.h>

#define N 256
#define Q 3329

// Export the function for Python ctypes
#ifdef _WIN32
__declspec(dllexport)
#endif
void poly_mul_c(const int32_t* a, const int32_t* b, int32_t* out) {
    int32_t c[512] = {0};
    
    // O(N^2) polynomial multiplication
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            c[i + j] = (c[i + j] + a[i] * b[j]) % Q;
        }
    }
    
    // Reduce modulo (X^256 + 1)
    for (int i = 0; i < N; i++) {
        int32_t val = (c[i] - c[i + N]) % Q;
        if (val < 0) {
            val += Q; // C modulo can be negative, Python's is strictly positive
        }
        out[i] = val;
    }
}
