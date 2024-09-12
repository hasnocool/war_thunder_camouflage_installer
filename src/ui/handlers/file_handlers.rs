use std::path::Path;
use reqwest;
use zip;
use std::fs::{self, File};
use std::io::{self, Cursor};
use crate::ui::WarThunderCamoInstaller;
use crate::path_utils;

// Function to install a skin from a given ZIP URL
pub fn install_skin(app: &mut WarThunderCamoInstaller, zip_url: &str) {
    if let Some(skins_directory) = &app.wt_skins_dir {
        let custom_structure = if app.use_custom_structure {
            Some(app.custom_structure.as_str())
        } else {
            None
        };

        let out_dir = if let Some(custom) = custom_structure {
            path_utils::generate_custom_path(skins_directory.as_path(), custom, app.current_camo.as_ref().unwrap())
        } else {
            skins_directory.join(&app.current_camo.as_ref().unwrap().vehicle_name)
        };

        println!("Downloading skin from {} to {:?}", zip_url, out_dir);

        // Spawn a new thread for downloading and installing the skin
        let out_dir_clone = out_dir.clone();
        let zip_url = zip_url.to_string();
        std::thread::spawn(move || {
            match download_and_install_skin(&zip_url, &out_dir_clone) {
                Ok(_) => println!("Skin installed successfully"),
                Err(e) => eprintln!("Failed to install skin: {}", e),
            }
        });

        app.error_message = Some("Skin installation started. Please wait...".to_string());
    } else {
        app.error_message = Some("War Thunder skins directory not selected".to_string());
    }
}

// Function to download and install a skin from a ZIP URL
fn download_and_install_skin(zip_url: &str, out_dir: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let response = reqwest::blocking::get(zip_url)?;
    let content = response.bytes()?;

    let mut zip = zip::ZipArchive::new(Cursor::new(content))?;
    fs::create_dir_all(out_dir)?;

    for i in 0..zip.len() {
        let mut file = zip.by_index(i)?;
        let outpath = out_dir.join(file.mangled_name());


if file.name().ends_with('/') {
    fs::create_dir_all(&outpath)?;
} else {
    if let Some(p) = outpath.parent() {
        if !p.exists() {
            fs::create_dir_all(p)?;
        }
    }
    let mut outfile = File::create(&outpath)?;
    io::copy(&mut file, &mut outfile)?;
}

#[cfg(unix)]
{
    use std::os::unix::fs::PermissionsExt;
    if let Some(mode) = file.unix_mode() {
        fs::set_permissions(&outpath, fs::Permissions::from_mode(mode))?;
    }
}
}

Ok(())
}

// Function to apply custom directory structure settings
pub fn apply_custom_structure(app: &mut WarThunderCamoInstaller) {
if app.use_custom_structure {
if let Some(camo) = &app.current_camo {
    if let Some(skins_dir) = &app.wt_skins_dir {
        let custom_path = crate::path_utils::generate_custom_path(
            skins_dir,
            &app.custom_structure,
            camo
        );
        app.error_message = Some(format!("Custom path: {}", custom_path.display()));
    } else {
        app.error_message = Some("War Thunder skins directory not set.".to_string());
    }
} else {
    app.error_message = Some("No camouflage selected.".to_string());
}
}
}