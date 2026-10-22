use collected_errors::*;
use std::num::ParseIntError;

// A fail-fast collector or skipped iterator must fail this test.
#[test]
fn processes_the_whole_batch_and_reports_every_failure() {
    let mut visited = Vec::new();
    let input = [0, 1, 128, 3, 126, 254, 255, 2];
    let error = process_batch(input.into_iter().inspect(|n| visited.push(*n)), "8").unwrap_err();
    assert_eq!(visited, input);
    let batch = error.downcast_inner_ref::<BatchErrors>().unwrap();
    assert_eq!(batch.0.len(), 5);
    let expected = [
        (true, "double_even(1)"),
        (false, "double_even(128)"),
        (true, "double_even(3)"),
        (false, "double_even(254)"),
        (true, "double_even(255)"),
    ];
    for (child, (odd, context)) in batch.0.iter().zip(expected) {
        assert_eq!(child.is_inner::<Odd>(), odd);
        assert_eq!(child.is_inner::<Overflow>(), !odd);
        assert_eq!(
            child
                .contexts()
                .map(ToString::to_string)
                .collect::<Vec<_>>(),
            [context]
        );
        assert!(render_report(&error).contains(context));
    }
    assert_eq!(render_report(&error).matches("Item error ").count(), 5);
    assert!(render_report(&error).contains("process batch"));
}

// Moving whole reports must preserve their existing allocation and diagnostics.
#[test]
fn collection_and_widening_keep_original_child_diagnostics() {
    let first = double_even(1).unwrap_err().context("first marker");
    let second = double_even(128).unwrap_err().context("second marker");
    let before = [&first, &second].map(|error| {
        (
            error.backtrace() as *const _ as usize,
            format!("{error:?}"),
            error.location().to_string(),
        )
    });
    let error = collect_results([Err(first), Ok(4), Err(second)]).unwrap_err();
    let widened: BatchReport = error.widen();
    let batch = widened.downcast_inner_ref::<BatchErrors>().unwrap();
    assert_eq!(batch.0.len(), 2);
    for (child, (address, report, location)) in batch.0.iter().zip(before) {
        assert_eq!(child.backtrace() as *const _ as usize, address);
        assert_eq!(format!("{child:?}"), report);
        assert_eq!(child.location().to_string(), location);
    }
    assert!(render_report(&widened).contains("first marker"));
    assert!(render_report(&widened).contains("second marker"));
}

#[test]
fn original_range_collects_both_odd_numbers() {
    let error = process_batch(0..5, "5").unwrap_err();
    let batch = error.downcast_inner_ref::<BatchErrors>().unwrap();
    assert_eq!(batch.0.len(), 2);
    assert!(batch.0.iter().all(|error| error.is_inner::<Odd>()));
    assert!(render_report(&error).contains("double_even(1)"));
    assert!(render_report(&error).contains("double_even(3)"));
}

#[test]
fn success_keeps_order_and_boundaries_and_empty_input() {
    assert_eq!(process_batch([126, 0, 2, 4], "4").unwrap(), [252, 0, 4, 8]);
    assert!(process_batch([], "0").unwrap().is_empty());
}

// Parsing must happen before even obtaining values from the iterator.
#[test]
fn prerequisite_error_propagates_before_iteration() {
    let mut visited = Vec::new();
    let error =
        process_batch([0, 2].into_iter().inspect(|n| visited.push(*n)), "many").unwrap_err();
    assert!(visited.is_empty());
    assert!(error.is_inner::<ParseIntError>());
    assert!(render_report(&error).contains("read expected count"));
    assert!(render_report(&error).contains("process batch"));
    assert!(!render_report(&error).contains("Item error "));
}

#[test]
fn finalization_error_propagates_after_successful_iteration() {
    let mut visited = Vec::new();
    let error =
        process_batch([0, 2, 4].into_iter().inspect(|n| visited.push(*n)), "4").unwrap_err();
    assert_eq!(visited, [0, 2, 4]);
    let mismatch = error.downcast_inner_ref::<CountMismatch>().unwrap();
    assert_eq!((mismatch.expected, mismatch.actual), (4, 3));
    assert!(render_report(&error).contains("check completed count"));
    assert!(render_report(&error).contains("process batch"));
}

#[test]
fn batch_failure_precedes_finalization_and_calls_do_not_share_state() {
    let first = process_batch([1, 128, 2], "99").unwrap_err();
    assert!(first.is_inner::<BatchErrors>());
    assert!(!first.is_inner::<CountMismatch>());
    assert_eq!(process_batch([0, 2], "2").unwrap(), [0, 4]);
    let second = process_batch([3], "1").unwrap_err();
    let batch = second.downcast_inner_ref::<BatchErrors>().unwrap();
    assert_eq!(batch.0.len(), 1);
    assert!(render_report(&second).contains("double_even(3)"));
    assert!(!render_report(&second).contains("double_even(128)"));
}
