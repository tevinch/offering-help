use role_spellings::Work;
use std::{
    error::Error,
    io::{self, Read, Write},
    process::ExitCode,
};

fn convert() -> Result<(), Box<dyn Error>> {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;
    let work: Work = serde_json::from_str(&input)?;
    let output = serde_json::to_string_pretty(&work)?;
    let mut stdout = io::stdout().lock();
    writeln!(stdout, "{output}")?;
    Ok(())
}

fn main() -> ExitCode {
    match convert() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("{error}");
            ExitCode::FAILURE
        }
    }
}
