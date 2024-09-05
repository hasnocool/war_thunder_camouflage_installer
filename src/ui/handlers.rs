use eframe::egui;
use std::path::{PathBuf, Path};
use std::sync::mpsc;
use rayon::prelude::*;
use crate::database;
use crate::image_utils;
use crate::file_operations;
use crate::path_utils;
use super::app::WarThunderCamoInstaller;
use super::handlers; // <-- Add this line
use image::GenericImageView;
use reqwest;
use zip;
use std::fs::{self, File};
use std::io::{self, Cursor};


pub fn set_wt_skins_directory(app: &mut WarThunderCamoInstaller) {
    if let Some(path) = rfd::FileDialog::new().pick_folder() {
        app.wt_skins_dir = Some(path);
    }
}

pub fn select_database_file(app: &mut WarThunderCamoInstaller) {
    if let Some(path) = rfd::FileDialog::new()
        .add_filter("SQLite Database", &["db", "sqlite"])
        .pick_file()
    {
        match rusqlite::Connection::open(&path) {
            Ok(new_conn) => {
                if let Err(e) = database::initialize_database(&new_conn) {
                    app.error_message = Some(format!("Failed to initialize database: {}", e));
                    return;
                }

                app.db_conn = Some(new_conn);
                app.error_message = Some(format!("Database set to: {}", path.display()));

                app.total_camos = database::update_total_camos(app.db_conn.as_ref().unwrap()).unwrap_or(0);
                app.current_index = 0;
                app.search_results.clear();
                app.search_mode = false;
                app.clear_images();

                if let Ok(Some((index, camo))) = app.fetch_camouflage_by_index(0) {
                    app.set_current_camo(index, camo);
                } else {
                    app.current_camo = None;
                    app.error_message = Some("Failed to load initial camouflage from new database.".to_string());
                }
            }
            Err(e) => {
                app.error_message = Some(format!("Failed to open database: {}", e));
            }
        }
    }
}

pub fn perform_search(app: &mut WarThunderCamoInstaller) {
    let query = if app.search_query.is_empty() { None } else { Some(app.search_query.as_str()) };

    // Ensure both branches return `&Vec<String>`
    let selected_tags = if app.tag_filtering_enabled {
        &app.selected_tags
    } else {
        &Vec::new() // Create a new empty Vec and return a reference to it
    };

    match app.fetch_camouflages(query, selected_tags) {
        Ok(results) => {
            app.search_results = results;
            app.search_mode = true;
            if !app.search_results.is_empty() {
                app.current_index = 0;
                app.set_current_camo(0, app.search_results[0].clone());
            } else {
                app.current_index = 0;
                app.current_camo = None;
                app.clear_images();
                app.error_message = Some("No results found".to_string());
            }
        }
        Err(e) => {
            app.error_message = Some(format!("Search error: {:?}", e));
            app.search_results.clear();
            app.current_camo = None;
            app.clear_images();
        }
    }
}


pub fn toggle_tag_filtering(app: &mut WarThunderCamoInstaller) {
    app.tag_filtering_enabled = !app.tag_filtering_enabled;
    perform_search(app);
}

pub fn tag_filters(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        ui.label("Filter by tags:");
        if ui.checkbox(&mut app.tag_filtering_enabled, "Enable Tag Filtering").changed() {
            super::handlers::toggle_tag_filtering(app); // Update the prefix to super::handlers
        }
    });

    if app.tag_filtering_enabled {
        ui.horizontal(|ui| {
            let all_tags: Vec<_> = app.available_tags.iter().chain(app.custom_tags.iter()).cloned().collect();
            let mut tags_changed = false;

            for tag in all_tags {
                let is_selected = app.selected_tags.contains(&tag);
                let mut checkbox_state = is_selected;

                if ui.checkbox(&mut checkbox_state, &tag).changed() {
                    super::handlers::toggle_tag(app, &tag); // Update the prefix to super::handlers
                    tags_changed = true;
                }
            }

            if tags_changed {
                super::handlers::perform_search(app); // Update the prefix to super::handlers
            }
        });
    }

    if ui.button("Apply Filter").clicked() {
        super::handlers::perform_search(app); // Update the prefix to super::handlers
    }
}



// Update the toggle_tag function to be used in the UI
pub fn toggle_tag(app: &mut WarThunderCamoInstaller, tag: &str) {
    if app.selected_tags.contains(&tag.to_string()) {
        app.selected_tags.retain(|t| t != tag);
    } else {
        app.selected_tags.push(tag.to_string());
    }
    perform_search(app);
}

pub fn add_custom_tags(app: &mut WarThunderCamoInstaller) {
    let new_tags: Vec<String> = app.custom_tags_input
        .split(',')
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect();
    app.custom_tags.extend(new_tags);
    app.custom_tags.sort();
    app.custom_tags.dedup();
    app.custom_tags_input.clear();
}

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

fn download_and_install_skin(zip_url: &str, out_dir: &Path) -> Result<(), Box<dyn std::error::Error>> {
    // Download the ZIP file
    let response = reqwest::blocking::get(zip_url)?;
    let content = response.bytes()?;

    // Create a cursor to read the ZIP content
    let mut zip = zip::ZipArchive::new(Cursor::new(content))?;

    // Create the output directory if it doesn't exist
    fs::create_dir_all(out_dir)?;

    // Extract the ZIP contents
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

        // Get and Set permissions
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

pub fn show_next_camo(app: &mut WarThunderCamoInstaller) {
    if app.search_mode {
        if app.current_index < app.search_results.len() - 1 {
            app.current_index += 1;
            if let Some(camo) = app.search_results.get(app.current_index) {
                app.set_current_camo(app.current_index, camo.clone());
            }
        }
    } else if app.current_index < app.total_camos - 1 {
        let next_index = app.current_index + 1;
        if let Ok(Some((index, camo))) = app.fetch_camouflage_by_index(next_index) {
            app.set_current_camo(index, camo);
        } else {
            app.error_message = Some("Failed to load the next camouflage.".to_string());
        }
    }
}

pub fn show_previous_camo(app: &mut WarThunderCamoInstaller) {
    if app.search_mode {
        if app.current_index > 0 {
            app.current_index -= 1;
            if let Some(camo) = app.search_results.get(app.current_index) {
                app.set_current_camo(app.current_index, camo.clone());
            }
        }
    } else if app.current_index > 0 {
        let prev_index = app.current_index - 1;
        if let Ok(Some((index, camo))) = app.fetch_camouflage_by_index(prev_index) {
            app.set_current_camo(index, camo);
        } else {
            app.error_message = Some("Failed to load the previous camouflage.".to_string());
        }
    }
}

pub fn update_image_grid(app: &WarThunderCamoInstaller, ctx: &egui::Context) {
    let mut loading = app.loading_images.lock().unwrap();
    if *loading {
        return;
    }

    let mut queue = app.image_load_queue.lock().unwrap();
    if queue.is_empty() {
        return;
    }

    *loading = true;
    let urls: Vec<String> = queue.drain(..).collect();
    let images = app.images.clone();
    let ctx = ctx.clone();
    let loading_images = app.loading_images.clone();

    std::thread::spawn(move || {
        let (tx, rx) = mpsc::channel();
        let tx = std::sync::Arc::new(std::sync::Mutex::new(tx));

        urls.par_iter().for_each_with(tx.clone(), |tx, url: &String| {
            if let Ok(image_data) = image_utils::load_image(url.clone()) {
                if let Ok(dynamic_image) = image::load_from_memory(&image_data) {
                    let (width, height) = dynamic_image.dimensions();
                    let rgba_image = dynamic_image.to_rgba8();
                    let image = egui::ColorImage::from_rgba_unmultiplied(
                        [width as usize, height as usize],
                        rgba_image.as_raw(),
                    );
                    let _ = tx.lock().unwrap().send((url.clone(), image));
                }
            }
        });

        drop(tx);

        for (url, image) in rx {
            ctx.request_repaint();
            let texture = ctx.load_texture(
                url.clone(),
                image,
                egui::TextureOptions::default(),
            );
            images.lock().unwrap().insert(url, texture);
        }

        *loading_images.lock().unwrap() = false;
    });
}

// Update load_current_camo_images to use a string slice
pub fn load_current_camo_images(app: &WarThunderCamoInstaller) {
    if let Some(camo) = &app.current_camo {
        let mut queue = app.image_load_queue.lock().unwrap();
        for url in &camo.image_urls {
            if !app.images.lock().unwrap().contains_key(url as &str) {
                queue.push_back(url.clone());
            }
        }
    }
}

pub fn export_tags(app: &mut WarThunderCamoInstaller) {
    if let Some(path) = rfd::FileDialog::new()
        .add_filter("JSON", &["json"])
        .save_file()
    {
        match app.export_tags(&path) {
            Ok(_) => app.error_message = Some("Tags exported successfully".to_string()),
            Err(e) => app.error_message = Some(format!("Failed to export tags: {}", e)),
        }
    }
}

pub fn import_tags(app: &mut WarThunderCamoInstaller) {
    if let Some(path) = rfd::FileDialog::new()
        .add_filter("JSON", &["json"])
        .pick_file()
    {
        match app.import_tags(&path) {
            Ok(_) => app.error_message = Some("Tags imported successfully".to_string()),
            Err(e) => app.error_message = Some(format!("Failed to import tags: {}", e)),
        }
    }
}

pub fn clear_cache(app: &mut WarThunderCamoInstaller) {
    if let Err(e) = image_utils::clear_cache() {
        app.error_message = Some(format!("Failed to clear cache: {}", e));
    } else {
        app.error_message = Some("Cache cleared successfully".to_string());
    }
}

pub fn show_custom_structure_popup(app: &mut WarThunderCamoInstaller, ctx: &egui::Context) {
    if app.show_custom_structure_popup {
        egui::Window::new("Custom Structure Settings")
            .collapsible(false)
            .resizable(false)
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    ui.label("Custom Structure:");
                    ui.text_edit_singleline(&mut app.custom_structure);
                });
                ui.checkbox(&mut app.use_custom_structure, "Use custom directory structure");
                if ui.button("Close").clicked() {
                    app.show_custom_structure_popup = false;
                }
            });
    }
}

pub fn show_about_popup(app: &mut WarThunderCamoInstaller, ctx: &egui::Context) {
    if app.show_about_popup {
        egui::Window::new("About").show(ctx, |ui| {
            ui.label("War Thunder Camouflage Installer v2024.09.02-072307");
            ui.label("Developed by hasnocool.");
            // Add more about information here...
            if ui.button("Close").clicked() {
                app.show_about_popup = false;
            }
        });
    }
}

pub fn show_import_popup(app: &mut WarThunderCamoInstaller, ctx: &egui::Context) {
    if app.show_import_popup {
        let mut show_import_popup = app.show_import_popup;
        egui::Window::new("Import Local Skin")
            .open(&mut show_import_popup)
            .show(ctx, |ui| {
                ui.label("Select directory for importing skins:");
                if ui.button("Browse").clicked() {
                    if let Some(path) = rfd::FileDialog::new().pick_folder() {
                        app.selected_import_dir = Some(path);
                    }
                }
                if let Some(selected_dir) = &app.selected_import_dir {
                    ui.label(format!("Selected directory: {}", selected_dir.display()));
                }
                if ui.button("Import").clicked() {
                    if let Some(selected_import_dir) = &app.selected_import_dir {
                        let result = file_operations::import_local_skin(
                            app.wt_skins_dir.as_ref().unwrap_or(&PathBuf::from(".")),
                            selected_import_dir,
                        );
                        match result {
                            Ok(_) => app.error_message = Some("Local skin imported successfully!".to_string()),
                            Err(e) => app.error_message = Some(format!("Failed to import skin: {}", e)),
                        }
                    } else {
                        app.error_message = Some("No directory selected for import.".to_string());
                    }
                    app.show_import_popup = false;
                }
            });
        app.show_import_popup = show_import_popup;
    }
}

// Additional helper functions

pub fn update_total_camos(app: &mut WarThunderCamoInstaller) {
    if let Some(db_conn) = &app.db_conn {
        match database::update_total_camos(db_conn) {
            Ok(count) => app.total_camos = count,
            Err(e) => app.error_message = Some(format!("Failed to update total camos: {}", e)),
        }
    }
}

// Implement refresh_available_tags in the UI update cycle
pub fn refresh_available_tags(app: &mut WarThunderCamoInstaller) {
    if let Some(db_conn) = &app.db_conn {
        match database::fetch_tags(db_conn, 0) {
            Ok(tags) => app.available_tags = tags,
            Err(e) => app.error_message = Some(format!("Failed to refresh available tags: {}", e)),
        }
    }
}

// Update apply_custom_structure to be used when the custom structure is changed
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

// Add a new function to update the application state
pub fn update_app_state(app: &mut WarThunderCamoInstaller) {
    update_total_camos(app);
    refresh_available_tags(app);
    // Add any other state updates here
}
// You can add more helper functions here as needed






















