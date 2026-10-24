use serde::de::Error as _;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::io::{self, Write};
use std::process::ExitCode;

#[derive(Debug, Deserialize, Serialize, PartialEq)]
struct User {
    id: u64,
    name: String,
}

fn user_from_response(response: &Value) -> Result<User, serde_json::Error> {
    let value = response
        .pointer("/data/user")
        .ok_or_else(|| serde_json::Error::custom("missing JSON Pointer /data/user"))?;
    User::deserialize(value)
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let response: Value = serde_json::from_reader(io::stdin().lock())?;
    let user = user_from_response(&response)?;
    let stdout = io::stdout();
    let mut output = stdout.lock();
    serde_json::to_writer(&mut output, &user)?;
    writeln!(output)?;
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("{error}");
            ExitCode::from(2)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn extracts_original_response_without_wrappers_or_mutation() {
        let response = json!({"data": {"user": {"id": 123, "name": "John"}}});
        let before = response.clone();
        assert!(serde_json::from_value::<User>(response.clone()).is_err());
        for _ in 0..2 {
            assert_eq!(
                user_from_response(&response).unwrap(),
                User {
                    id: 123,
                    name: "John".into()
                }
            );
        }
        assert_eq!(response, before);
    }

    #[test]
    fn standalone_user_still_deserializes_normally() {
        let user: User = serde_json::from_str(r#"{"id":123,"name":"John"}"#).unwrap();
        assert_eq!(
            user,
            User {
                id: 123,
                name: "John".into()
            }
        );
    }

    #[test]
    fn unicode_and_unrelated_data_do_not_change() {
        let response = json!({"data": {"user": {"id": 42, "name": "李 🌱", "extra": true}, "other": [1, null]}, "meta": "keep"});
        let before = serde_json::to_string(&response).unwrap();
        assert_eq!(user_from_response(&response).unwrap().name, "李 🌱");
        assert_eq!(serde_json::to_string(&response).unwrap(), before);
    }

    #[test]
    fn distinguishes_missing_path_from_present_null() {
        let missing = user_from_response(&json!({"data": {}}))
            .unwrap_err()
            .to_string();
        let null = user_from_response(&json!({"data": {"user": null}}))
            .unwrap_err()
            .to_string();
        assert!(
            missing.contains("missing JSON Pointer /data/user"),
            "{missing}"
        );
        assert!(null.contains("invalid type: null"), "{null}");
    }

    #[test]
    fn rejects_invalid_user_fields() {
        for user in [
            json!({"name":"John"}),
            json!({"id":-1,"name":"John"}),
            json!({"id":"123","name":"John"}),
            json!({"id":123,"name":null}),
        ] {
            assert!(user_from_response(&json!({"data":{"user":user}})).is_err());
        }
    }
}
