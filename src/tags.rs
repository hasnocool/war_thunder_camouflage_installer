use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
pub struct TagCollection {
    pub available_tags: Vec<String>,
    pub custom_tags: Vec<String>,
}