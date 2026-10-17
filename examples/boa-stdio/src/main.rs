use boa_engine::{Context, Source};
use boa_stdio_example::install_stdio;
use std::{io, process::ExitCode};

fn main() -> ExitCode {
    let mut context = Context::default();
    let result = install_stdio(&mut context, io::stdin(), io::stdout(), io::stderr())
        .and_then(|()| context.eval(Source::from_bytes(include_str!("../demo.js"))));
    match result {
        Ok(_) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("{error}");
            ExitCode::FAILURE
        }
    }
}
