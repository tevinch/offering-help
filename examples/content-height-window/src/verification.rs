//! Scripted checks in the real native application, using GPUI input dispatch.
//! These are simulated input events, not operating-system or human clicks.
use super::{Example, MIN_HEIGHT};
use gpui_kit::*;
use std::time::{Duration, Instant};

#[derive(Clone, Copy, Debug)]
struct Snapshot {
    rows: usize,
    rendered_rows: usize,
    callbacks: usize,
    resizes: usize,
    width: f32,
    height: f32,
    measured: f32,
}

fn snapshot(handle: AnyWindowHandle, view: &Entity<Example>, cx: &AsyncApp) -> Snapshot {
    cx.update(|cx| {
        handle
            .update(cx, |_, window, cx| {
                let state = view.read(cx);
                let observed = &state.observations;
                Snapshot {
                    rows: state.rows,
                    rendered_rows: observed.rendered_rows.get(),
                    callbacks: observed.callbacks.get(),
                    resizes: observed.resizes.get(),
                    width: f32::from(window.viewport_size().width),
                    height: f32::from(window.viewport_size().height),
                    measured: observed.measured.get(),
                }
            })
            .expect("native window remains open")
    })
}

async fn pause(cx: &AsyncApp) {
    cx.background_executor()
        .timer(Duration::from_millis(20))
        .await;
}

async fn checkpoint(
    handle: AnyWindowHandle,
    view: &Entity<Example>,
    rows: usize,
    width: f32,
    label: &str,
    cx: &AsyncApp,
) -> Result<Snapshot, String> {
    let deadline = Instant::now() + Duration::from_secs(3);
    let settled = loop {
        let value = snapshot(handle, view, cx);
        if value.callbacks > 0
            && value.rows == rows
            && value.rendered_rows == rows
            && (value.width - width).abs() < 0.5
            && (value.height - value.measured.max(MIN_HEIGHT)).abs() <= 0.5
        {
            break value;
        }
        if Instant::now() > deadline {
            return Err(format!(
                "{label}: native geometry did not settle: {value:?}"
            ));
        }
        pause(cx).await;
    };
    // Request three new native frames. The hook must really run each time,
    // while the stable result must not cause more resize requests.
    let mut previous = settled;
    for _ in 0..3 {
        cx.update(|cx| handle.update(cx, |_, window, _| window.refresh()).unwrap());
        let deadline = Instant::now() + Duration::from_secs(2);
        loop {
            pause(cx).await;
            let next = snapshot(handle, view, cx);
            if next.callbacks > previous.callbacks {
                if next.rows != rows
                    || next.rendered_rows != rows
                    || next.width != settled.width
                    || next.height != settled.height
                    || next.resizes != settled.resizes
                {
                    return Err(format!("{label}: unstable native frame: {next:?}"));
                }
                previous = next;
                break;
            }
            if Instant::now() > deadline {
                return Err(format!("{label}: requested native frame never prepainted"));
            }
        }
    }
    println!("CHECKPOINT {label}: {previous:?}");
    Ok(previous)
}

async fn click(
    handle: AnyWindowHandle,
    view: &Entity<Example>,
    index: usize,
    cx: &AsyncApp,
) -> Result<(), String> {
    let bounds = cx.update(|cx| view.read(cx).observations.buttons.borrow()[index]);
    let position = bounds.center();
    let viewport = snapshot(handle, view, cx);
    if bounds.left() < px(0.)
        || bounds.top() < px(0.)
        || f32::from(bounds.right()) > viewport.width
        || f32::from(bounds.bottom()) > viewport.height
    {
        return Err(format!(
            "button {index} outside the native viewport: {bounds:?}"
        ));
    }
    let events = [
        MouseMoveEvent {
            position,
            pressed_button: None,
            modifiers: Modifiers::default(),
        }
        .to_platform_input(),
        MouseDownEvent {
            position,
            button: MouseButton::Left,
            modifiers: Modifiers::default(),
            click_count: 1,
            first_mouse: false,
        }
        .to_platform_input(),
        MouseUpEvent {
            position,
            button: MouseButton::Left,
            modifiers: Modifiers::default(),
            click_count: 1,
        }
        .to_platform_input(),
    ];
    for event in events {
        let old = snapshot(handle, view, cx).callbacks;
        cx.update(|cx| {
            handle
                .update(cx, |_, window, cx| {
                    window.dispatch_event(event, cx);
                    window.refresh();
                })
                .unwrap()
        });
        let deadline = Instant::now() + Duration::from_secs(2);
        while snapshot(handle, view, cx).callbacks <= old {
            if Instant::now() > deadline {
                return Err("input frame never completed".into());
            }
            pause(cx).await;
        }
    }
    Ok(())
}

async fn run(handle: AnyWindowHandle, view: Entity<Example>, cx: &AsyncApp) -> Result<(), String> {
    assert!(!cx.is_test(), "verification requires a native application");
    let initial = checkpoint(handle, &view, 2, 520., "initial", cx).await?;
    for (index, rows, label) in [
        (0, 3, "add"),
        (0, 4, "add-again"),
        (1, 3, "remove"),
        (0, 4, "add-after-remove"),
        (1, 3, "remove-again"),
        (1, 2, "baseline-content"),
    ] {
        click(handle, &view, index, cx).await?;
        checkpoint(handle, &view, rows, 520., label, cx).await?;
    }
    cx.update(|cx| {
        handle
            .update(cx, |_, window, _| window.resize(size(px(360.), px(500.))))
            .unwrap()
    });
    let narrow = checkpoint(handle, &view, 2, 360., "narrow-wrap", cx).await?;
    if narrow.height <= initial.height {
        return Err("narrow width did not add wrapped text height".into());
    }
    click(handle, &view, 0, cx).await?;
    checkpoint(handle, &view, 3, 360., "add-after-wrap", cx).await?;
    cx.update(|cx| {
        handle
            .update(cx, |_, window, _| window.resize(size(px(760.), px(500.))))
            .unwrap()
    });
    let wide = checkpoint(handle, &view, 3, 760., "wide-wrap", cx).await?;
    click(handle, &view, 2, cx).await?;
    let reset = checkpoint(handle, &view, 2, 760., "reset", cx).await?;
    if reset.height >= wide.height || reset.height >= initial.height {
        return Err("reset or wider text did not reduce native height".into());
    }
    for (rows, label) in [(1, "one-row"), (0, "empty"), (0, "remove-at-zero")] {
        click(handle, &view, 1, cx).await?;
        checkpoint(handle, &view, rows, 760., label, cx).await?;
    }
    for rows in 1..=6 {
        click(handle, &view, 0, cx).await?;
        checkpoint(handle, &view, rows, 760., "fill", cx).await?;
    }
    click(handle, &view, 0, cx).await?;
    checkpoint(handle, &view, 6, 760., "disabled-add", cx).await?;
    click(handle, &view, 2, cx).await?;
    checkpoint(handle, &view, 2, 760., "final-reset", cx).await?;
    Ok(())
}

pub fn start(handle: AnyWindowHandle, view: Entity<Example>, cx: &mut App) {
    cx.spawn(async move |cx| {
        if let Err(error) = run(handle, view, cx).await {
            eprintln!("Native verification FAILED: {error}");
            std::process::exit(1);
        }
        println!("Native verification passed (simulated GPUI pointer events, real native window).");
        cx.update(|cx| cx.quit());
    })
    .detach();
}
