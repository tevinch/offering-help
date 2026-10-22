use schemars_field_contracts::{
    combined_schema, request_schema, response_schema, CombinedSample, Sample,
};
use serde_json::json;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let input =
        json!({"name": "ignored input", "name2": "request value", "name3": "ignored internal"});
    let mut sample: Sample = serde_json::from_value(input.clone())?;
    let mut combined: CombinedSample = serde_json::from_value(input.clone())?;
    let decoded = json!({"name": sample.name, "name2": sample.name2, "name3": sample.name3});
    sample.name = "response value".into();
    combined.name = sample.name.clone();
    let report = json!({
        "request_schema": request_schema(),
        "response_schema": response_schema(),
        "combined_schema": combined_schema(),
        "input": input,
        "decoded": decoded,
        "response": serde_json::to_value(sample)?,
        "combined_response": serde_json::to_value(combined)?,
    });
    println!("{}", serde_json::to_string_pretty(&report)?);
    Ok(())
}
