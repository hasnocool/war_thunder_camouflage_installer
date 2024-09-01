use std::path::Path;
use rfd::FileDialog;
use zip::ZipArchive;
use std::fs;
use std::io;

pub fn import_local_skin(
    _skins_directory: &Path,
    selected_import_dir: &Path,
) -> Result<(), Box<dyn std::error::Error>> {
    let file_path = FileDialog::new()
        .add_filter("Archive", &["zip", "rar"])
        .pick_file()
        .ok_or("No file selected for import")?;

    println!("Importing skin from {:?}", file_path);
    let file = fs::File::open(&file_path)?;
    let mut archive = ZipArchive::new(file)?;

    let out_dir = selected_import_dir.to_path_buf();

    fs::create_dir_all(&out_dir)?;

    for i in 0..archive.len() {
        let mut file = archive.by_index(i)?;
        let outpath = out_dir.join(file.mangled_name());

        if file.name().ends_with('/') {
            fs::create_dir_all(&outpath)?;
        } else {
            if let Some(p) = outpath.parent() {
                if !p.exists() {
                    fs::create_dir_all(p)?;
                }
            }
            let mut outfile = fs::File::create(&outpath)?;
            io::copy(&mut file, &mut outfile)?;
        }
    }

    println!("Skin imported successfully to {:?}", out_dir);
    Ok(())
}