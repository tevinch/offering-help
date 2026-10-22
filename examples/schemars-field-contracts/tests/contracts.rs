use schemars_field_contracts::{
    combined_schema, request_schema, response_schema, CombinedSample, Sample,
};
use serde_json::{json, Value};

fn properties(schema: &Value) -> Vec<&str> {
    schema["properties"]
        .as_object()
        .unwrap()
        .keys()
        .map(String::as_str)
        .collect()
}

#[test]
fn combined_document_contains_the_requested_annotations() {
    let schema = combined_schema();
    assert_eq!(properties(&schema), vec!["name", "name2"]);
    assert_eq!(schema["properties"]["name"]["readOnly"], true);
    assert_eq!(schema["properties"]["name"]["default"], "");
    assert_eq!(schema["properties"]["name2"]["writeOnly"], true);
    assert_eq!(schema["required"], json!(["name2"]));
    assert!(schema["properties"].get("name3").is_none());
}

#[test]
fn unmodified_attributes_generate_directional_contracts() {
    let request = request_schema();
    let response = response_schema();
    assert_eq!(properties(&request), vec!["name2"]);
    assert_eq!(request["required"], json!(["name2"]));
    assert_eq!(request["properties"]["name2"]["writeOnly"], true);
    assert_eq!(properties(&response), vec!["name"]);
    assert_eq!(response["required"], json!(["name"]));
    assert_eq!(response["properties"]["name"]["readOnly"], true);
}

#[test]
fn real_serde_request_and_response_match_the_directional_schemas() {
    let input =
        json!({"name": "ignored input", "name2": "request value", "name3": "ignored internal"});
    let mut sample: Sample = serde_json::from_value(input.clone()).unwrap();
    let mut combined: CombinedSample = serde_json::from_value(input.clone()).unwrap();
    assert_eq!(
        (&sample.name, &sample.name2, &sample.name3),
        (&String::new(), &"request value".to_string(), &String::new())
    );
    assert_eq!(
        (&combined.name, &combined.name2, &combined.name3),
        (&sample.name, &sample.name2, &sample.name3)
    );
    sample.name = "response value".into();
    combined.name = sample.name.clone();
    let output = serde_json::to_value(sample).unwrap();
    assert_eq!(output, json!({"name": "response value"}));
    assert_eq!(serde_json::to_value(combined).unwrap(), output);

    let request_validator = jsonschema::validator_for(&request_schema()).unwrap();
    let response_validator = jsonschema::validator_for(&response_schema()).unwrap();
    assert!(request_validator.is_valid(&input));
    assert!(request_validator.is_valid(&json!({"name2": "minimal request"})));
    assert!(response_validator.is_valid(&output));
    for bad in [json!({}), json!({"name2": 42})] {
        assert!(!request_validator.is_valid(&bad));
        assert!(serde_json::from_value::<Sample>(bad.clone()).is_err());
        assert!(serde_json::from_value::<CombinedSample>(bad).is_err());
    }
    assert!(!response_validator.is_valid(&json!({})));
    assert!(!response_validator.is_valid(&json!({"name": 42})));
}

#[test]
fn annotations_do_not_change_required_or_fill_in_defaults() {
    let schema = combined_schema();
    let validator = jsonschema::validator_for(&schema).unwrap();
    let request = json!({"name2": "request value"});
    assert!(validator.is_valid(&request));
    assert_eq!(request, json!({"name2": "request value"}));
    assert!(validator.is_valid(&json!({"name": "provided", "name2": "request value"})));
    assert!(!validator.is_valid(&json!({"name": "response value"})));
    assert!(!validator.is_valid(&json!({"name2": 42})));
    assert!(!validator.is_valid(&json!({"name": 42, "name2": "request value"})));
}

#[test]
fn default_schema_is_a_negative_control_for_the_combined_field_list() {
    let original = request_schema();
    assert!(original["properties"].get("name").is_none());
    assert_ne!(properties(&original), vec!["name", "name2"]);
}

#[test]
fn command_runs_the_complete_example_and_emits_valid_json() {
    let result = std::process::Command::new(env!("CARGO_BIN_EXE_schemars-field-contracts"))
        .output()
        .unwrap();
    assert!(
        result.status.success(),
        "{}",
        String::from_utf8_lossy(&result.stderr)
    );
    let report: Value = serde_json::from_slice(&result.stdout).unwrap();
    assert_eq!(report["request_schema"], request_schema());
    assert_eq!(report["response_schema"], response_schema());
    assert_eq!(report["combined_schema"], combined_schema());
    assert_eq!(
        report["decoded"],
        json!({"name": "", "name2": "request value", "name3": ""})
    );
    assert_eq!(report["response"], json!({"name": "response value"}));
    assert_eq!(report["combined_response"], report["response"]);
    assert!(jsonschema::is_valid(
        &report["request_schema"],
        &report["input"]
    ));
    assert!(jsonschema::is_valid(
        &report["response_schema"],
        &report["response"]
    ));
}
