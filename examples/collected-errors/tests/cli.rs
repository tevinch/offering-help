use std::process::{Command, Output};

fn run(scenario: &str, backtrace: bool) -> Output {
    Command::new(env!("CARGO_BIN_EXE_collected-errors"))
        .arg(scenario)
        .env("RUST_LIB_BACKTRACE", if backtrace { "1" } else { "0" })
        .env("RUST_BACKTRACE", if backtrace { "1" } else { "0" })
        .output()
        .unwrap()
}

#[test]
fn mixed_cli_reports_every_failure_with_captured_traces() {
    let output = run("mixed", true);
    assert_eq!(output.status.code(), Some(1));
    assert_eq!(
        String::from_utf8(output.stdout).unwrap(),
        "Visited: [0, 1, 128, 3, 126, 254, 255, 2]\n"
    );
    let report = String::from_utf8(output.stderr).unwrap();
    assert_eq!(report.matches("Item error ").count(), 5);
    for value in [1, 128, 3, 254, 255] {
        assert!(report.contains(&format!("double_even({value})")));
    }
    assert!(report.contains("process batch"));
    assert_eq!(report.matches("Backtrace (captured)").count(), 6);
    for child in report.split("Item error ").skip(1) {
        assert!(child.contains("collected_errors::double_even"));
    }
}

#[test]
fn original_cli_reports_both_errors_when_backtraces_disabled() {
    let output = run("original", false);
    assert_eq!(output.status.code(), Some(1));
    assert_eq!(
        String::from_utf8(output.stdout).unwrap(),
        "Visited: [0, 1, 2, 3, 4]\n"
    );
    let report = String::from_utf8(output.stderr).unwrap();
    assert_eq!(report.matches("Item error ").count(), 2);
    assert!(report.contains("double_even(1)"));
    assert!(report.contains("double_even(3)"));
    assert!(!report.contains("Backtrace (captured)"));
}

#[test]
fn cli_preserves_before_and_after_errors_and_corrected_success() {
    let before = run("before", false);
    assert_eq!(before.status.code(), Some(1));
    assert_eq!(String::from_utf8(before.stdout).unwrap(), "Visited: []\n");
    assert!(
        String::from_utf8(before.stderr)
            .unwrap()
            .contains("read expected count")
    );
    let after = run("after", false);
    assert_eq!(after.status.code(), Some(1));
    assert_eq!(
        String::from_utf8(after.stdout).unwrap(),
        "Visited: [0, 2, 4]\n"
    );
    let report = String::from_utf8(after.stderr).unwrap();
    assert!(report.contains("expected 4 results, got 3"));
    assert!(report.contains("check completed count"));
    let success = run("success", false);
    assert!(success.status.success());
    assert_eq!(
        String::from_utf8(success.stdout).unwrap(),
        "Visited: [0, 2, 4, 126]\nValues: [0, 4, 8, 252]\n"
    );
    assert!(success.stderr.is_empty());
}

#[test]
fn unknown_scenario_returns_usage() {
    let output = run("missing", false);
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8(output.stderr).unwrap().contains("Usage:"));
}
