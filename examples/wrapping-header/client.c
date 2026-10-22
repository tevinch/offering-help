#include "counter.h"
#include <assert.h>
#include <stddef.h>
#include <stdio.h>

int main(void) {
    assert(sizeof(Counter) == counter_size());
#ifdef __cplusplus
    assert(alignof(Counter) == counter_alignment());
#else
    assert(_Alignof(Counter) == counter_alignment());
#endif
    assert(offsetof(Counter, value) == counter_value_offset());
    assert(sizeof(((Counter *)0)->value) == sizeof(uint32_t));

    Counter zero = {0x12, 0};
    zero = counter_add(zero, 0);
    assert(zero.marker == 0x12 && zero.value == 0);
    zero = counter_add(zero, 42);
    assert(zero.marker == 0x12 && zero.value == 42);

    Counter edge = {0x7A, UINT32_MAX};
    edge = counter_add(edge, 1);
    assert(edge.marker == 0x7A && edge.value == 0);
    edge = counter_add(edge, 7);
    assert(edge.marker == 0x7A && edge.value == 7);
    edge = counter_add(edge, UINT32_MAX);
    assert(edge.marker == 0x7A && edge.value == 6);
    puts("PASS: layout, marker, zero, normal addition and repeated wrapping");
    return 0;
}
