//! Synchronous byte I/O bindings for a small Boa host.
use boa_engine::{
    Context, JsNativeError, JsResult, JsValue, NativeFunction, js_string,
    object::{ObjectInitializer, builtins::JsUint8Array},
    property::Attribute,
};
use std::{
    cell::RefCell,
    io::{self, Read, Write},
};

// Contains Rust streams only: no garbage-collected JavaScript values.
struct Streams {
    input: RefCell<Box<dyn Read>>,
    output: RefCell<Box<dyn Write>>,
    diagnostics: RefCell<Box<dyn Write>>,
}

/// Install `std.read`, `std.write`, and `std.err` in a fresh context.
/// Call once, before evaluating the synchronous script.
pub fn install_stdio(
    context: &mut Context,
    input: impl Read + 'static,
    output: impl Write + 'static,
    diagnostics: impl Write + 'static,
) -> JsResult<()> {
    context.insert_data(Streams {
        input: RefCell::new(Box::new(input)),
        output: RefCell::new(Box::new(output)),
        diagnostics: RefCell::new(Box::new(diagnostics)),
    });
    let std = ObjectInitializer::new(context)
        .function(NativeFunction::from_fn_ptr(read), js_string!("read"), 1)
        .function(NativeFunction::from_fn_ptr(write), js_string!("write"), 1)
        .function(NativeFunction::from_fn_ptr(err), js_string!("err"), 1)
        .build();
    context.register_global_property(js_string!("std"), std, Attribute::all())
}

fn streams(context: &Context) -> JsResult<&Streams> {
    context.get_data::<Streams>().ok_or_else(|| {
        JsNativeError::error()
            .with_message("stdio is not installed")
            .into()
    })
}

fn uint8_argument(args: &[JsValue]) -> JsResult<JsUint8Array> {
    args.first()
        .and_then(JsValue::as_object)
        .ok_or_else(|| JsNativeError::typ().with_message("expected Uint8Array"))
        .and_then(|object| {
            JsUint8Array::from_object(object)
                .map_err(|_| JsNativeError::typ().with_message("expected Uint8Array"))
        })
        .map_err(Into::into)
}

fn io_error(operation: &str, error: io::Error) -> boa_engine::JsError {
    JsNativeError::error()
        .with_message(format!("{operation}: {error}"))
        .into()
}

// The empty-view case precedes Read::read, which can also return 0 at EOF.
fn read_bytes(reader: &mut dyn Read, mut bytes: Vec<u8>) -> io::Result<Option<Vec<u8>>> {
    if bytes.is_empty() {
        return Ok(Some(bytes));
    }
    loop {
        match reader.read(&mut bytes) {
            Ok(0) => return Ok(None),
            Ok(count) => {
                bytes.truncate(count);
                return Ok(Some(bytes));
            }
            Err(error) if error.kind() == io::ErrorKind::Interrupted => continue,
            Err(error) => return Err(error),
        }
    }
}

fn read(_: &JsValue, args: &[JsValue], context: &mut Context) -> JsResult<JsValue> {
    let array = uint8_argument(args)?;
    // Public API validates attachment and bounds, including zero-length views.
    let destination = array.to_vec(context)?;
    let result = read_bytes(&mut **streams(context)?.input.borrow_mut(), destination);
    match result {
        Ok(Some(bytes)) => {
            for (index, byte) in bytes.iter().enumerate() {
                array.set(index, *byte, true, context)?;
            }
            Ok(JsValue::new(bytes.len()))
        }
        Ok(None) => Ok(JsValue::null()),
        Err(error) => Err(io_error("stdin read", error)),
    }
}

fn write(_: &JsValue, args: &[JsValue], context: &mut Context) -> JsResult<JsValue> {
    let bytes = uint8_argument(args)?.to_vec(context)?;
    if !bytes.is_empty() {
        let mut output = streams(context)?.output.borrow_mut();
        output
            .write_all(&bytes)
            .and_then(|()| output.flush())
            .map_err(|error| io_error("stdout write", error))?;
    }
    Ok(JsValue::new(bytes.len()))
}

fn err(_: &JsValue, args: &[JsValue], context: &mut Context) -> JsResult<JsValue> {
    let text = args
        .first()
        .and_then(JsValue::as_string)
        .ok_or_else(|| JsNativeError::typ().with_message("expected string"))?
        .to_std_string_escaped();
    let mut output = streams(context)?.diagnostics.borrow_mut();
    output
        .write_all(text.as_bytes())
        .and_then(|()| output.flush())
        .map_err(|error| io_error("stderr write", error))?;
    Ok(JsValue::undefined())
}

#[cfg(test)]
mod tests {
    use super::read_bytes;
    use std::io::{self, Cursor, Read};

    struct InterruptedOnce<R> {
        inner: R,
        interrupted: bool,
    }
    impl<R: Read> Read for InterruptedOnce<R> {
        fn read(&mut self, bytes: &mut [u8]) -> io::Result<usize> {
            if !self.interrupted {
                self.interrupted = true;
                return Err(io::ErrorKind::Interrupted.into());
            }
            self.inner.read(bytes)
        }
    }
    struct Failed;
    impl Read for Failed {
        fn read(&mut self, _: &mut [u8]) -> io::Result<usize> {
            Err(io::ErrorKind::PermissionDenied.into())
        }
    }

    // The integration tests additionally require conversion of these Result
    // variants into distinct observable JavaScript outcomes.
    #[test]
    fn read_result_distinguishes_empty_view_eof_interrupted_and_failure() {
        let mut input = Cursor::new(vec![0, 255]);
        assert_eq!(read_bytes(&mut input, vec![]).unwrap(), Some(vec![]));
        let mut input = InterruptedOnce {
            inner: input,
            interrupted: false,
        };
        assert_eq!(
            read_bytes(&mut input, vec![0; 4]).unwrap(),
            Some(vec![0, 255])
        );
        assert_eq!(read_bytes(&mut input, vec![0; 4]).unwrap(), None);
        assert_eq!(
            read_bytes(&mut Failed, vec![0; 4]).unwrap_err().kind(),
            io::ErrorKind::PermissionDenied
        );
    }
}
