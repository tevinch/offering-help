use dioxus::prelude::*;
use dioxus_primitives::{dioxus_attributes::attributes, virtual_list::VirtualList};
use std::rc::Rc;

const ROW_HEIGHT: u32 = 48;

// The data stays in one signal. Rows do not need to implement Clone.
struct NotCloneableListElement {
    name: String,
}

fn main() {
    dioxus::launch(App);
}

fn scroll_to_row(
    index: usize,
    viewport: Signal<Option<Rc<MountedData>>>,
    mut status: Signal<String>,
) {
    let Some(element) = viewport.read().clone() else {
        status.set("The list is not mounted yet.".into());
        return;
    };
    spawn(async move {
        // This is exact because the real row height, including its border,
        // is 48px. estimate_size alone would not enforce that condition.
        let offset = (0.0, index as f64 * f64::from(ROW_HEIGHT)).into();
        match element.scroll(offset, ScrollBehavior::Instant).await {
            Ok(()) => status.set(format!("Requested row {index}.")),
            Err(error) => status.set(format!("Could not scroll: {error}")),
        }
    });
}

#[component]
fn App() -> Element {
    let mut list = use_signal(|| {
        (1..40000)
            .map(|i| NotCloneableListElement {
                name: format!("Test_{i}"),
            })
            .collect::<Vec<_>>()
    });
    let mut viewport = use_signal(|| None::<Rc<MountedData>>);
    let mut target = use_signal(|| "30000".to_string());
    let mut status = use_signal(|| "Enter a row index or use Go to top.".to_string());
    let ready = viewport.read().is_some();
    let count = list.len();
    let first_label = list.read()[0].name.clone();

    rsx! {
        style { {include_str!("../style.css")} }
        main {
            h1 { "Virtual list navigation" }
            p { "Jump to a row without clearing or remounting the list." }
            p { "Rows: " strong { id: "row-count", "{count}" } " · zero-based indexes · 48px rows" }
            form {
                onsubmit: move |event| {
                    event.prevent_default();
                    // Use the submitted named field: Enter and button submit
                    // take exactly the same path, without keyboard timing hacks.
                    let text = match event.get_first("index") {
                        Some(FormValue::Text(value)) => value,
                        _ => String::new(),
                    };
                    match text.trim().parse::<usize>() {
                        Ok(index) if index < list.len() => scroll_to_row(index, viewport, status),
                        _ => status.set(format!("Enter a whole row index from 0 to {}.", list.len() - 1)),
                    }
                },
                label { r#for: "target-index", "Row index" }
                input {
                    id: "target-index", name: "index", r#type: "text", inputmode: "numeric",
                    value: "{target}",
                    oninput: move |event| target.set(event.value()),
                }
                button { r#type: "submit", disabled: !ready, "Go to row" }
                button {
                    r#type: "button", disabled: !ready,
                    onclick: move |_| scroll_to_row(0, viewport, status),
                    "Go to top"
                }
            }
            p { id: "status", role: "status", "{status}" }
            div { class: "label-editor",
                label { r#for: "first-label", "First row label" }
                input {
                    id: "first-label", value: first_label,
                    oninput: move |event| list.write()[0].name = event.value(),
                }
                small { "Edit it, jump away, then return to row 0." }
            }
            VirtualList {
                // Event handlers go through the forwarded attributes list.
                // Keep the internal id; the component uses it for its scroll listener.
                attributes: attributes!(div {
                    class: "dx-virtual-list-container",
                    onmounted: move |event: MountedEvent| viewport.set(Some(event.data())),
                }),
                count: list.len(),
                buffer: 100usize,
                estimate_size: |_| ROW_HEIGHT,
                render_item: move |idx: usize| {
                    let row = list.get(idx).expect("virtual index is within the unchanged list");
                    let name = row.name.as_str();
                    rsx! { article { class: "dx-virtual-list-card", key: "{idx}", "{idx} {name}" } }
                },
            }
        }
    }
}
