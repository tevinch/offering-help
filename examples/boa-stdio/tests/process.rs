use std::{
    io::Write,
    process::{Command, Stdio},
};

fn execute(input: &[u8]) -> std::process::Output {
    let mut child = Command::new(env!("CARGO_BIN_EXE_boa-stdio-example"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let write_result = child.stdin.take().unwrap().write_all(input);
    if let Err(error) = write_result {
        assert_eq!(error.kind(), std::io::ErrorKind::BrokenPipe);
    }
    child.wait_with_output().unwrap()
}

// A Rust echo without executing JS cannot produce the calculated diagnostics.
#[test]
fn real_pipes_preserve_binary_multiple_and_empty_frames() {
    let fixture = [
        7, 0, 0, 0, 0, 127, 128, 255, 226, 130, 172, 0, 0, 0, 0, 1, 0, 0, 0, 42,
    ];
    let result = execute(&fixture);
    assert!(result.status.success(), "{:?}", result.stderr);
    assert_eq!(result.stdout, fixture);
    assert_eq!(
        result.stderr,
        b"frame 1: 7 bytes, sum=1038\nframe 2: 0 bytes, sum=0\nframe 3: 1 bytes, sum=42\n"
    );
}
#[test]
fn clean_eof_at_a_frame_boundary_succeeds() {
    let result = execute(&[]);
    assert!(result.status.success());
    assert!(result.stdout.is_empty());
    assert!(result.stderr.is_empty());
}
#[test]
fn truncation_and_oversize_fail_without_emitting_a_success_frame() {
    for (fixture, message) in [
        (vec![1, 0], "truncated header"),
        (vec![3, 0, 0, 0, 0, 255], "truncated payload"),
        (vec![1, 0, 1, 0], "frame exceeds 65536 bytes"),
        (vec![255, 255, 255, 255], "frame exceeds 65536 bytes"),
    ] {
        let result = execute(&fixture);
        assert!(
            !result.status.success(),
            "input {fixture:?} unexpectedly succeeded"
        );
        assert!(result.stdout.is_empty());
        assert!(String::from_utf8(result.stderr).unwrap().contains(message));
    }
}
#[test]
fn maximum_example_payload_is_accepted() {
    let mut fixture = vec![0, 0, 1, 0];
    fixture.extend(std::iter::repeat_n(255, 65536));
    let result = execute(&fixture);
    assert!(result.status.success());
    assert_eq!(result.stdout.len(), fixture.len());
    assert!(result.stdout == fixture, "65536-byte frame changed");
    assert_eq!(result.stderr, b"frame 1: 65536 bytes, sum=16711680\n");
}
