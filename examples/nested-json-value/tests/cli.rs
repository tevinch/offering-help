use std::io::Write;
use std::process::{Command, Output, Stdio};

fn run(input: &str) -> Output {
    let mut child = Command::new(env!("CARGO_BIN_EXE_nested-json-value"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(input.as_bytes())
        .unwrap();
    child.wait_with_output().unwrap()
}

#[test]
fn reads_original_api_response_to_complete_typed_output() {
    let result = run(r#"{"data":{"user":{"id":123,"name":"John"}}}"#);
    assert!(
        result.status.success(),
        "{}",
        String::from_utf8_lossy(&result.stderr)
    );
    assert_eq!(result.stdout, b"{\"id\":123,\"name\":\"John\"}\n");
    assert!(result.stderr.is_empty());
}

#[test]
fn invalid_inputs_return_two_without_partial_user_output() {
    for input in [
        "{",
        "",
        r#"{"data":{}}"#,
        r#"{"data":{"user":null}}"#,
        r#"{"data":{"user":{"id":"123","name":"John"}}}"#,
        r#"{"id":123,"name":"John"}"#,
        r#"{"data":{"user":{"id":123,"name":"John"}}} {}"#,
    ] {
        let result = run(input);
        assert_eq!(result.status.code(), Some(2), "input {input:?}");
        assert!(result.stdout.is_empty(), "input {input:?}");
        assert!(!result.stderr.is_empty(), "input {input:?}");
    }
}
