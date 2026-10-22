use schemars::{generate::SchemaSettings, JsonSchema};
use serde::{Deserialize, Serialize};
use serde_json::Value;

/// Original Serde attributes: generate a separate schema for each direction.
#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct Sample {
    #[serde(skip_deserializing)]
    pub name: String,
    #[serde(skip_serializing)]
    pub name2: String,
    #[serde(skip)]
    pub name3: String,
}

/// A complete field list for documentation, with the same Serde behavior.
#[derive(Debug, Deserialize, Serialize, JsonSchema)]
pub struct CombinedSample {
    #[serde(skip_deserializing)]
    #[schemars(!skip_deserializing, default, extend("readOnly" = true))]
    pub name: String,
    #[serde(skip_serializing)]
    pub name2: String,
    #[serde(skip)]
    pub name3: String,
}

pub fn request_schema() -> Value {
    serde_json::to_value(
        SchemaSettings::draft2020_12()
            .for_deserialize()
            .into_generator()
            .into_root_schema_for::<Sample>(),
    )
    .unwrap()
}

pub fn response_schema() -> Value {
    serde_json::to_value(
        SchemaSettings::draft2020_12()
            .for_serialize()
            .into_generator()
            .into_root_schema_for::<Sample>(),
    )
    .unwrap()
}

pub fn combined_schema() -> Value {
    serde_json::to_value(
        SchemaSettings::draft2020_12()
            .for_deserialize()
            .into_generator()
            .into_root_schema_for::<CombinedSample>(),
    )
    .unwrap()
}
