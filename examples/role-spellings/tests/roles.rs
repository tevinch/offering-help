use role_spellings::{PersonRole, Work};
use strum::ParseError;

#[test]
fn accepts_the_requested_spellings_as_the_same_role() {
    for (text, expected) in [
        ("cast-member", PersonRole::CastMember),
        ("cast_member", PersonRole::CastMember),
        ("casTMember", PersonRole::CastMember),
        ("CastMember", PersonRole::CastMember),
        ("CAST-MEMBER", PersonRole::CastMember),
        ("cAsT_mEmBeR", PersonRole::CastMember),
        ("executive-producer", PersonRole::ExecutiveProducer),
        ("executive_producer", PersonRole::ExecutiveProducer),
        ("ExecutiveProducer", PersonRole::ExecutiveProducer),
        ("eXeCuTiVe-PrOdUcEr", PersonRole::ExecutiveProducer),
        ("EXECUTIVE_PRODUCER", PersonRole::ExecutiveProducer),
        ("DiReCtOr", PersonRole::Director),
        ("TRANSLATOR", PersonRole::Translator),
    ] {
        assert_eq!(text.parse::<PersonRole>(), Ok(expected), "{text}");
    }
}

#[test]
fn rejects_unsupported_spellings_instead_of_removing_every_separator() {
    for text in [
        "",
        "asdf",
        "cast__member",
        "cast--member",
        "c-astmember",
        "cast member",
        " cast-member",
        "cast-member ",
        "\tDirector",
        "DİRECTOR",
        "dіrector",
        "caſt-member",
        "cast–member",
        "executive.producer",
    ] {
        assert_eq!(
            text.parse::<PersonRole>(),
            Err(ParseError::VariantNotFound),
            "{text:?}"
        );
    }
}

#[test]
fn parses_the_entire_document_and_round_trips_content_with_canonical_roles() {
    let input = r#"{
        "title": "An example work",
        "affiliated": [
            {"role": "cAsT_mEmBeR", "names": ["Example, Alex", "Example, Sam"]},
            {"role": "ExecutiveProducer", "names": ["Example, Casey"]},
            {"role": "DiReCtOr", "names": ["Example, Robin"]},
            {"role": "Transl\u0061tor", "names": ["O'Neil, A. \"Q\"", "李, 明"]}
        ]
    }"#;
    let work: Work = serde_json::from_str(input).unwrap();
    assert_eq!(work.affiliated.len(), 4);
    assert_eq!(work.affiliated[0].role, PersonRole::CastMember);
    assert_eq!(work.affiliated[1].role, PersonRole::ExecutiveProducer);
    assert_eq!(work.affiliated[2].role, PersonRole::Director);
    assert_eq!(work.affiliated[3].role, PersonRole::Translator);
    let output = serde_json::to_value(&work).unwrap();
    let expected = serde_json::json!({
        "title": "An example work",
        "affiliated": [
            {"role": "cast-member", "names": ["Example, Alex", "Example, Sam"]},
            {"role": "executive-producer", "names": ["Example, Casey"]},
            {"role": "director", "names": ["Example, Robin"]},
            {"role": "translator", "names": ["O'Neil, A. \"Q\"", "李, 明"]}
        ]
    });
    assert_eq!(output, expected);
    let round_trip: Work = serde_json::from_value(output).unwrap();
    assert_eq!(round_trip, work);
}

#[test]
fn structured_input_reports_bad_role_and_can_be_corrected() {
    let bad =
        r#"{"title":"Example","affiliated":[{"role":"cast__member","names":["Example, Alex"]}]}"#;
    let error = serde_json::from_str::<Work>(bad).unwrap_err().to_string();
    assert!(error.contains("cast__member"), "{error}");
    assert!(error.contains("cast-member"), "{error}");
    let corrected = bad.replace("cast__member", "cast_member");
    let work: Work = serde_json::from_str(&corrected).unwrap();
    assert_eq!(work.affiliated[0].role, PersonRole::CastMember);
    assert_eq!(work.affiliated[0].names, ["Example, Alex"]);
}

#[test]
fn rejects_non_string_roles() {
    for value in ["null", "12", "[]", "{}", "true"] {
        let text = format!(r#"{{"title":"Example","affiliated":[{{"role":{value},"names":[]}}]}}"#);
        assert!(serde_json::from_str::<Work>(&text).is_err(), "{text}");
    }
}
