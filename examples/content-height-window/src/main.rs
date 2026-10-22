use gpui_kit::component::{ActiveTheme, Disableable, button::*, h_flex, v_flex};
use gpui_kit::*;
use std::{
    cell::{Cell, RefCell},
    rc::Rc,
};

mod verification;

const MIN_HEIGHT: f32 = 100.;

#[derive(Default)]
struct Observations {
    callbacks: Cell<usize>,
    resizes: Cell<usize>,
    measured: Cell<f32>,
    rendered_rows: Cell<usize>,
    buttons: RefCell<Vec<Bounds<Pixels>>>,
}

struct Example {
    rows: usize,
    observations: Rc<Observations>,
    fit: bool,
    trace: bool,
}

impl Render for Example {
    fn render(&mut self, _: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
        let rows = self.rows;
        let observations = self.observations.clone();
        let toolbar_observations = self.observations.clone();
        let content_observations = self.observations.clone();
        let fit = self.fit;
        let trace = self.trace;
        let content = v_flex()
            .w_full()
            .flex_shrink_0()
            .p_4()
            .gap_3()
            .child(div().text_lg().child("Content height"))
            .child("Add or remove rows, then resize the window width. This paragraph wraps to demonstrate that the required height depends on the current width.")
            .child(
                h_flex()
                    .gap_2()
                    .on_children_prepainted(move |bounds, _, _| {
                        *toolbar_observations.buttons.borrow_mut() = bounds;
                    })
                    .child(Button::new("add").label("Add row").disabled(rows == 6).on_click(cx.listener(
                        |this, _, _, cx| {
                            this.rows = (this.rows + 1).min(6);
                            cx.notify();
                        },
                    )))
                    .child(Button::new("remove").label("Remove row").on_click(cx.listener(
                        |this, _, _, cx| {
                            this.rows = this.rows.saturating_sub(1);
                            cx.notify();
                        },
                    )))
                    .child(Button::new("reset").label("Reset").on_click(cx.listener(
                        |this, _, _, cx| {
                            this.rows = 2;
                            cx.notify();
                        },
                    ))),
            )
            .children((0..rows).map(|index| {
                div()
                    .p_2()
                    .border_1()
                    .border_color(cx.theme().border)
                    .rounded_md()
                    .child(format!("Row {}", index + 1))
            }))
            .on_children_prepainted(move |bounds, _, _| {
                content_observations.rendered_rows.set(bounds.len().saturating_sub(3));
            });

        div()
            .size_full()
            .bg(cx.theme().background)
            .text_color(cx.theme().foreground)
            .child(content)
            .on_children_prepainted(move |bounds, window, cx| {
                observations.callbacks.set(observations.callbacks.get() + 1);
                // The single child owns all padding and has intrinsic height.
                // Do not put h_full()/flex_1() on that measured child.
                let measured = bounds[0].size.height;
                observations.measured.set(f32::from(measured));
                let viewport = window.viewport_size();
                if trace {
                    println!(
                        "{{\"callbacks\":{},\"resizes\":{},\"rows\":{},\"width\":{},\"height\":{},\"measured\":{}}}",
                        observations.callbacks.get(), observations.resizes.get(), rows, f32::from(viewport.width), f32::from(viewport.height), f32::from(measured),
                    );
                }
                let scale = window.scale_factor();
                let height = px(((f32::from(measured) * scale).ceil() / scale).max(MIN_HEIGHT));
                if fit && (f32::from(viewport.height - height)).abs() >= 1. / scale {
                    let observations = observations.clone();
                    window.defer(cx, move |window, _| {
                        let current = window.viewport_size();
                        // A new width needs a new measurement, not stale geometry.
                        if current.width == viewport.width && current.height != height {
                            observations.resizes.set(observations.resizes.get() + 1);
                            window.resize(size(current.width, height));
                        }
                    });
                }
            })
    }
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let fit = !args.iter().any(|arg| arg == "--no-fit");
    let trace = args.iter().any(|arg| arg == "--trace");
    let verify = args.iter().any(|arg| arg == "--verify");
    gpui_kit::application().run(move |cx| {
        gpui_kit::init(cx);
        cx.on_window_closed(|cx, _| cx.quit()).detach();
        let (window, view) = gpui_kit::open_window(
            WindowOptions {
                window_bounds: Some(WindowBounds::Windowed(Bounds::centered(
                    None,
                    size(px(520.), px(700.)),
                    cx,
                ))),
                titlebar: Some(TitlebarOptions {
                    title: Some("Content height".into()),
                    ..Default::default()
                }),
                window_min_size: Some(size(px(360.), px(MIN_HEIGHT))),
                ..Default::default()
            },
            cx,
            |_, cx| {
                cx.new(|_| Example {
                    rows: 2,
                    observations: Rc::new(Observations::default()),
                    fit,
                    trace,
                })
            },
        )
        .expect("open content-height window");
        cx.activate(true);
        if verify {
            verification::start(window, view, cx);
        }
    });
}
