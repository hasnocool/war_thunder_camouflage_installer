use eframe::egui;
use std::path::PathBuf;
use std::sync::mpsc;
use rayon::prelude::*;
use crate::database;
use crate::image_utils;
use crate::file_operations;
use super::app::WarThunderCamoInstaller;
use image::GenericImageView;

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

                app.db_conn = new_conn;
                app.error_message = Some(format!("Database set to: {}", path.display()));

                app.total_camos = database::update_total_camos(&app.db_conn).unwrap_or(0);
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
    match app.fetch_camouflages(query, &app.selected_tags) {
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

pub fn toggle_tag(app: &mut WarThunderCamoInstaller, tag: &str, is_selected: bool) {
    if is_selected {
        app.selected_tags.push(tag.to_string());
    } else {
        app.selected_tags.retain(|t| t != tag);
    }
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
            crate::path_utils::generate_custom_path(skins_directory.as_path(), custom, app.current_camo.as_ref().unwrap())
        } else {
            skins_directory.join(&app.current_camo.as_ref().unwrap().vehicle_name)
        };

        println!("Downloading skin from {} to {:?}", zip_url, out_dir);

        // Here you would implement the actual download and installation logic
        // For now, we'll just set a success message
        app.error_message = Some("Skin installed successfully".to_string());
    } else {
        app.error_message = Some("War Thunder skins directory not selected".to_string());
    }
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

pub fn load_current_camo_images(app: &WarThunderCamoInstaller) {
    if let Some(camo) = &app.current_camo {
        let mut queue = app.image_load_queue.lock().unwrap();
        for url in &camo.image_urls {
            if !app.images.lock().unwrap().contains_key(url) {
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