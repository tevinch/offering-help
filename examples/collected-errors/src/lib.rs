use eros::{Context, ErrorUnion, IntoUnion, ReshapeUnion, context};
use std::{fmt, num::ParseIntError};
use thiserror::Error;

#[derive(Debug, Error)]
#[error("an odd number was provided")]
pub struct Odd;

#[derive(Debug, Error)]
#[error("doubling the number overflowed")]
pub struct Overflow;

pub type ItemError = ErrorUnion<(Odd, Overflow)>;

#[derive(Debug)]
pub struct BatchErrors(pub Vec<ItemError>);

impl fmt::Display for BatchErrors {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} items failed", self.0.len())
    }
}

impl std::error::Error for BatchErrors {}

#[derive(Debug, Error)]
#[error("expected {expected} results, got {actual}")]
pub struct CountMismatch {
    pub expected: usize,
    pub actual: usize,
}

pub type BatchReport = ErrorUnion<(ParseIntError, BatchErrors, CountMismatch)>;

#[context("double_even({})", value)]
pub fn double_even(value: u8) -> Result<u8, ItemError> {
    if !value.is_multiple_of(2) {
        return Err(Odd).union();
    }
    value.checked_mul(2).ok_or(Overflow).union()
}

pub fn collect_results(
    results: impl IntoIterator<Item = Result<u8, ItemError>>,
) -> eros::Result<Vec<u8>, (BatchErrors,)> {
    let mut values = Vec::new();
    let mut errors = Vec::new();
    for result in results {
        match result {
            Ok(value) => values.push(value),
            // Move the whole union; its diagnostics stay with it.
            Err(error) => errors.push(error),
        }
    }
    if errors.is_empty() {
        Ok(values)
    } else {
        Err(BatchErrors(errors))
            .union()
            .context("collect doubled values")
    }
}

#[context("process batch")]
pub fn process_batch(
    numbers: impl IntoIterator<Item = u8>,
    expected_count: &str,
) -> Result<Vec<u8>, BatchReport> {
    // A separate failure before the loop uses the same return type.
    let expected = expected_count
        .parse::<usize>()
        .union()
        .context("read expected count")?;
    let values = collect_results(numbers.into_iter().map(double_even)).widen()?;
    // This step only runs when the complete batch succeeded.
    let count = if values.len() == expected {
        Ok(())
    } else {
        Err(CountMismatch {
            expected,
            actual: values.len(),
        })
    };
    count.union().context("check completed count")?;
    Ok(values)
}

pub fn render_report(error: &BatchReport) -> String {
    let mut report = format!("{error:?}");
    // Error::source is a single chain; explicitly report these sibling errors.
    if let Some(batch) = error.downcast_inner_ref::<BatchErrors>() {
        for (index, child) in batch.0.iter().enumerate() {
            report.push_str(&format!("\n\nItem error {}:\n{child:?}", index + 1));
        }
    }
    report
}
