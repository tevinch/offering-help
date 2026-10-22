use collected_errors::{process_batch, render_report};
use std::process::ExitCode;

fn main() -> ExitCode {
    let scenario = std::env::args().nth(1).unwrap_or_else(|| "mixed".into());
    let (numbers, expected): (Vec<u8>, &str) = match scenario.as_str() {
        "mixed" => (vec![0, 1, 128, 3, 126, 254, 255, 2], "8"),
        "original" => ((0..5).collect(), "5"),
        "success" => (vec![0, 2, 4, 126], "4"),
        "before" => (vec![0, 2, 4], "many"),
        "after" => (vec![0, 2, 4], "4"),
        _ => {
            eprintln!("Usage: collected-errors [mixed|original|success|before|after]");
            return ExitCode::from(2);
        }
    };
    let mut visited = Vec::new();
    let result = process_batch(numbers.into_iter().inspect(|n| visited.push(*n)), expected);
    println!("Visited: {visited:?}");
    match result {
        Ok(values) => {
            println!("Values: {values:?}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("{}", render_report(&error));
            ExitCode::FAILURE
        }
    }
}
