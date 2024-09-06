use eframe::egui;
use std::path::PathBuf;
use super::app::WarThunderCamoInstaller;
use crate::file_operations;

// Function to show the custom structure popup
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

// Function to show the about popup
pub fn show_about_popup(app: &mut WarThunderCamoInstaller, ctx: &egui::Context) {
    if app.show_about_popup {
        egui::Window::new("About").show(ctx, |ui| {
            ui.label("War Thunder Camouflage Installer v2024.09.02-072307");
            ui.label("Developed by hasnocool.");
            if ui.button("Close").clicked() {
                app.show_about_popup = false;
            }
        });
    }
}

// Function to show the import local skin popup
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