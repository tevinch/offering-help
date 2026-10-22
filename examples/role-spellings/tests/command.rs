use std::{
    io::Write,
    process::{Command, Output, Stdio},
};

fn run(input: &str) -> Output {
    let mut child = Command::new(env!("CARGO_BIN_EXE_role-spellings"))
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
fn command_parses_real_stdin_and_writes_canonical_roles_without_losing_content() {
    let result = run(include_str!("../fixtures/work.json"));
    assert!(result.status.success(), "{:?}", result);
    assert!(result.stderr.is_empty());
    let actual: serde_json::Value = serde_json::from_slice(&result.stdout).unwrap();
    let expected: serde_json::Value =
        serde_json::from_str(include_str!("../fixtures/expected.json")).unwrap();
    assert_eq!(actual, expected);
}

#[test]
fn invalid_role_fails_without_output_and_corrected_input_completes() {
    let bad =
        r#"{"title":"Example","affiliated":[{"role":"cast__member","names":["Example, Alex"]}]}"#;
    let result = run(bad);
    assert!(!result.status.success());
    assert!(result.stdout.is_empty());
    let error = String::from_utf8(result.stderr).unwrap();
    assert!(error.contains("cast__member"), "{error}");
    assert!(error.contains("cast-member"), "{error}");
    let corrected = run(&bad.replace("cast__member", "cast_member"));
    assert!(corrected.status.success(), "{:?}", corrected);
    let actual: serde_json::Value = serde_json::from_slice(&corrected.stdout).unwrap();
    assert_eq!(
        actual,
        serde_json::json!({"title":"Example","affiliated":[{"role":"cast-member","names":["Example, Alex"]}]})
    );
}

#[test]
fn malformed_document_does_not_produce_successful_output() {
    let result = run("{broken");
    assert!(!result.status.success());
    assert!(result.stdout.is_empty());
    assert!(!result.stderr.is_empty());
}

#[test]
fn fields_outside_the_example_schema_are_rejected_rather_than_discarded() {
    for input in [
        r#"{"title":"Example","year":2026,"affiliated":[]}"#,
        r#"{"title":"Example","affiliated":[{"role":"Director","names":[],"credit":"keep me"}]}"#,
    ] {
        let result = run(input);
        assert!(!result.status.success(), "{input}");
        assert!(result.stdout.is_empty());
        let error = String::from_utf8(result.stderr).unwrap();
        assert!(error.contains("unknown field"), "{error}");
    }
}
