use std::mem::{align_of, offset_of, size_of};
use std::num::Wrapping;

pub type WrappedU32 = Wrapping<u32>;

#[repr(C)]
pub struct Counter {
    pub marker: u8,
    pub value: WrappedU32,
}

#[unsafe(no_mangle)]
pub extern "C" fn counter_add(mut counter: Counter, amount: u32) -> Counter {
    counter.value += Wrapping(amount);
    counter
}

#[unsafe(no_mangle)]
pub extern "C" fn counter_size() -> usize {
    size_of::<Counter>()
}

#[unsafe(no_mangle)]
pub extern "C" fn counter_alignment() -> usize {
    align_of::<Counter>()
}

#[unsafe(no_mangle)]
pub extern "C" fn counter_value_offset() -> usize {
    offset_of!(Counter, value)
}
