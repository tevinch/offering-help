use boa_engine::{
    Context, JsValue, Source, js_string,
    object::builtins::{JsArrayBuffer, JsUint8Array},
    property::Attribute,
};
use boa_stdio_example::install_stdio;
use std::{
    cell::RefCell,
    io::{self, Cursor, Read, Write},
    rc::Rc,
};

#[derive(Clone, Default)]
struct Output(Rc<RefCell<Vec<u8>>>);
impl Write for Output {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        self.0.borrow_mut().extend_from_slice(bytes);
        Ok(bytes.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
fn host(
    input: impl Read + 'static,
    output: impl Write + 'static,
    err: impl Write + 'static,
) -> Context {
    let mut context = Context::default();
    install_stdio(&mut context, input, output, err).unwrap();
    context
}
fn run(context: &mut Context, source: &str) -> JsValue {
    context.eval(Source::from_bytes(source)).unwrap()
}
fn text(value: JsValue) -> String {
    value.as_string().unwrap().to_std_string_escaped()
}

// Catches ignoring offsets, copying unread tail bytes, treating empty reads as EOF,
// consuming input for an empty view, and returning fake EOF after a short read.
#[test]
fn read_write_views_preserve_sentinels_and_distinguish_empty_and_eof() {
    let output = Output::default();
    let mut context = host(
        Cursor::new(vec![0, 127, 128, 255, 226, 130, 172]),
        output.clone(),
        io::sink(),
    );
    let result = run(
        &mut context,
        r#"
        const data = new Uint8Array([91, 92, 93, 94, 95, 96]);
        const empty = std.read(data.subarray(2, 2));
        let counts = [];
        for (;;) {
            const count = std.read(data.subarray(1, 5));
            counts.push(count);
            if (count === null) break;
            if (std.write(data.subarray(1, 1 + count)) !== count) throw Error('write count');
        }
        JSON.stringify([empty, counts, Array.from(data)]);
    "#,
    );
    assert_eq!(text(result), "[0,[4,3,null],[91,226,130,172,255,96]]");
    assert_eq!(*output.0.borrow(), [0, 127, 128, 255, 226, 130, 172]);
}

struct InterruptedThenByte(bool);
impl Read for InterruptedThenByte {
    fn read(&mut self, dst: &mut [u8]) -> io::Result<usize> {
        if !self.0 {
            self.0 = true;
            return Err(io::ErrorKind::Interrupted.into());
        }
        dst[0] = 255;
        Ok(1)
    }
}
#[test]
fn interrupted_read_retries_through_registered_callback() {
    let output = Output::default();
    let mut context = host(InterruptedThenByte(false), output.clone(), io::sink());
    let value = run(
        &mut context,
        "let b = new Uint8Array(4); let n = std.read(b); std.write(b.subarray(0,n)); n",
    );
    assert_eq!(value.as_number(), Some(1.0));
    assert_eq!(*output.0.borrow(), [255]);
}
struct BrokenRead;
impl Read for BrokenRead {
    fn read(&mut self, _: &mut [u8]) -> io::Result<usize> {
        Err(io::Error::other("read fixture failed"))
    }
}
#[test]
fn real_read_error_is_a_js_exception_instead_of_eof() {
    let mut context = host(BrokenRead, io::sink(), io::sink());
    let value = run(
        &mut context,
        "try { std.read(new Uint8Array(2)); 'fake EOF' } catch(e) { String(e) }",
    );
    assert!(text(value).contains("read fixture failed"));
}
struct ShortWrite {
    output: Output,
    fail_after_prefix: bool,
    interrupted: bool,
}
impl Write for ShortWrite {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        if self.interrupted {
            self.interrupted = false;
            return Err(io::ErrorKind::Interrupted.into());
        }
        if self.fail_after_prefix && !self.output.0.borrow().is_empty() {
            return Err(io::Error::other("write fixture failed"));
        }
        let count = bytes.len().min(2);
        self.output.write(&bytes[..count])
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
#[test]
fn short_and_interrupted_writes_complete_the_view_once() {
    let output = Output::default();
    let mut context = host(
        io::empty(),
        ShortWrite {
            output: output.clone(),
            fail_after_prefix: false,
            interrupted: true,
        },
        io::sink(),
    );
    assert_eq!(
        run(
            &mut context,
            "std.write(new Uint8Array([91,0,128,255,92]).subarray(1,4))"
        )
        .as_number(),
        Some(3.0)
    );
    assert_eq!(*output.0.borrow(), [0, 128, 255]);
}
#[test]
fn partial_write_failure_throws_without_replaying_the_prefix() {
    let output = Output::default();
    let mut context = host(
        io::empty(),
        ShortWrite {
            output: output.clone(),
            fail_after_prefix: true,
            interrupted: false,
        },
        io::sink(),
    );
    let value = run(
        &mut context,
        "try { std.write(new Uint8Array([0,128,255,42])); 'fake success' } catch(e) { String(e) }",
    );
    assert!(text(value).contains("write fixture failed"));
    assert_eq!(*output.0.borrow(), [0, 128]);
}
#[test]
fn unicode_diagnostics_keep_newlines_and_stay_off_stdout() {
    let output = Output::default();
    let err = Output::default();
    let mut context = host(io::empty(), output.clone(), err.clone());
    run(
        &mut context,
        "std.err('诊断 café ☕\\nnext\\n'); std.write(new Uint8Array([0,255]));",
    );
    assert_eq!(*output.0.borrow(), [0, 255]);
    assert_eq!(*err.0.borrow(), "诊断 café ☕\nnext\n".as_bytes());
}
#[test]
fn wrong_types_and_detached_buffers_throw_type_errors() {
    let mut context = host(Cursor::new(vec![42]), io::sink(), io::sink());
    let buffer = JsArrayBuffer::new(3, &mut context).unwrap();
    let detached = JsUint8Array::from_array_buffer(buffer.clone(), &mut context).unwrap();
    buffer.detach(&JsValue::undefined()).unwrap();
    context
        .register_global_property(js_string!("detached"), detached, Attribute::all())
        .unwrap();
    let result = run(
        &mut context,
        r#"
        let errors = 0;
        for (const value of [undefined, {}, [], 'x', new Uint16Array(2), detached]) {
            for (const call of [std.read, std.write]) {
                try { call(value); } catch(e) { if (e instanceof TypeError) errors++; }
            }
        }
        try { std.err(42); } catch(e) { if (e instanceof TypeError) errors++; }
        const b = new Uint8Array(1);
        JSON.stringify([errors, std.read(b), b[0], std.write(new Uint8Array(0))]);
    "#,
    );
    assert_eq!(text(result), "[13,1,42,0]");
}
#[test]
fn diagnostic_write_error_is_observable() {
    let output = Output::default();
    let mut context = host(
        io::empty(),
        io::sink(),
        ShortWrite {
            output: output.clone(),
            fail_after_prefix: true,
            interrupted: false,
        },
    );
    let result = run(
        &mut context,
        "try { std.err('abcd'); 'fake success' } catch(e) { String(e) }",
    );
    assert!(text(result).contains("write fixture failed"));
    assert_eq!(*output.0.borrow(), b"ab");
}

struct SmallChunks(Cursor<Vec<u8>>);
impl Read for SmallChunks {
    fn read(&mut self, bytes: &mut [u8]) -> io::Result<usize> {
        let count = bytes.len().min(2);
        self.0.read(&mut bytes[..count])
    }
}
// Catches a single-read header/payload implementation, omitted script execution,
// premature boundary EOF, dropping empty frames, or skipping the JS checksum.
#[test]
fn frame_script_accumulates_short_reads_and_processes_multiple_frames() {
    let output = Output::default();
    let err = Output::default();
    let fixture = vec![
        7, 0, 0, 0, 0, 127, 128, 255, 226, 130, 172, 0, 0, 0, 0, 1, 0, 0, 0, 42,
    ];
    let mut context = host(
        SmallChunks(Cursor::new(fixture.clone())),
        output.clone(),
        err.clone(),
    );
    context
        .eval(Source::from_bytes(include_str!("../demo.js")))
        .unwrap();
    assert_eq!(*output.0.borrow(), fixture);
    assert_eq!(
        *err.0.borrow(),
        b"frame 1: 7 bytes, sum=1038\nframe 2: 0 bytes, sum=0\nframe 3: 1 bytes, sum=42\n"
    );
}
