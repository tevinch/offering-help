// A synchronous byte echo; stdout is reserved for complete binary frames.
const MAX_PAYLOAD = 64 * 1024;

function readExact(destination, atBoundary, label) {
    let offset = 0;
    while (offset < destination.length) {
        const count = std.read(destination.subarray(offset));
        if (count === null) {
            if (atBoundary && offset === 0) return false;
            throw new Error(`truncated ${label}`);
        }
        if (count === 0) throw new Error(`no read progress in ${label}`);
        offset += count;
    }
    return true;
}

let frame = 0;
for (;;) {
    const header = new Uint8Array(4);
    if (!readExact(header, true, "header")) break;
    const length = new DataView(header.buffer).getUint32(0, true);
    if (length > MAX_PAYLOAD) throw new Error(`frame exceeds ${MAX_PAYLOAD} bytes`);
    const payload = new Uint8Array(length);
    readExact(payload, false, "payload");
    let sum = 0;
    for (const byte of payload) sum += byte;
    std.write(header);
    std.write(payload);
    frame++;
    std.err(`frame ${frame}: ${length} bytes, sum=${sum}\n`);
}
