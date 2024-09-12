use std::path::PathBuf;

pub fn find_war_thunder_directory() -> Option<PathBuf> {
    let paths_to_check: Vec<PathBuf>;
    
    if cfg!(target_os = "windows") {
        paths_to_check = vec![
            PathBuf::from("C:\\Program Files (x86)\\Steam\\steamapps\\common\\War Thunder"),
            PathBuf::from("C:\\Program Files\\WarThunder"),
        ];
    } else if cfg!(target_os = "macos") {
        paths_to_check = vec![
            PathBuf::from("/Users/Shared/War Thunder"),
            PathBuf::from("/Users/[YourUsername]/Library/Application Support/Steam/steamapps/common/War Thunder"),
        ];
    } else if cfg!(target_os = "linux") {
        paths_to_check = vec![
            PathBuf::from("~/.local/share/Steam/steamapps/common/War Thunder"),
            PathBuf::from("~/WarThunder"),
        ];
    } else {
        return None;
    }

    paths_to_check.into_iter().find(|path| path.exists())
}

pub fn find_user_skins_directory() -> Option<PathBuf> {
    find_war_thunder_directory().map(|wt_dir| wt_dir.join("UserSkins"))
}
