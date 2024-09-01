use std::path::{Path, PathBuf};
use crate::data::Camouflage;

pub fn generate_custom_path(base_dir: &Path, custom_structure: &str, camo: &Camouflage) -> PathBuf {
    let mut path = custom_structure.to_string();
    path = path.replace("%USERSKINS", base_dir.to_str().unwrap_or(""));
    path = path.replace("%NICKNAME", &camo.nickname);
    path = path.replace("%SKIN_NAME", &camo.vehicle_name);
    path = path.replace("%VEHICLE", &camo.vehicle_name);

    PathBuf::from(path)
}