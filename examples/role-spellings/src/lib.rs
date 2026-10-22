use serde::{Deserialize, Deserializer, Serialize, de};
use std::fmt;
use strum::EnumString;

/// Three conventional spellings for multiword roles, with ASCII case ignored.
#[derive(Debug, Clone, Copy, PartialEq, Eq, EnumString, Serialize)]
#[strum(ascii_case_insensitive)]
#[serde(rename_all = "kebab-case")]
pub enum PersonRole {
    // Explicit aliases replace the implicit variant name, so keep it here too.
    #[strum(
        serialize = "CastMember",
        serialize = "cast-member",
        serialize = "cast_member"
    )]
    CastMember,
    #[strum(
        serialize = "ExecutiveProducer",
        serialize = "executive-producer",
        serialize = "executive_producer"
    )]
    ExecutiveProducer,
    Director,
    Translator,
}

impl<'de> Deserialize<'de> for PersonRole {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        struct RoleVisitor;

        impl de::Visitor<'_> for RoleVisitor {
            type Value = PersonRole;

            fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
                formatter.write_str("a person role string")
            }

            fn visit_str<E: de::Error>(self, value: &str) -> Result<PersonRole, E> {
                value.parse().map_err(|_| {
                    E::unknown_variant(
                        value,
                        &[
                            "cast-member",
                            "executive-producer",
                            "director",
                            "translator",
                        ],
                    )
                })
            }
        }

        deserializer.deserialize_str(RoleVisitor)
    }
}

#[derive(Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Affiliated {
    pub role: PersonRole,
    pub names: Vec<String>,
}

/// Small consumer input format; this is not the complete Hayagriva format.
#[derive(Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Work {
    pub title: String,
    pub affiliated: Vec<Affiliated>,
}
