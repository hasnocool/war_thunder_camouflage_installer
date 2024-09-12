use eframe::egui;
use super::app::WarThunderCamoInstaller;
use crate::ui::handlers::database_handlers;
use crate::ui::handlers::navigation_handlers;
use crate::ui::handlers::file_handlers;
use crate::ui::handlers::image_handlers;
use crate::ui::handlers::general_handlers;
use crate::ui::handlers::general_handlers::set_wt_skins_directory;
use crate::ui::handlers::general_handlers::change_database_file;
use std::collections::HashMap;

// Menu bar function
pub fn menu_bar(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    egui::menu::bar(ui, |ui| {
        // File Menu
        ui.menu_button("File", |ui| {
            if ui.button("Change War Thunder Skins Directory").clicked() {
                set_wt_skins_directory(app);
                ui.close_menu();
            }
            if ui.button("Change Database File").clicked() {
                change_database_file(app);
                ui.close_menu();
            }
            if ui.button("Clear Cache").clicked() {
                image_handlers::clear_cache(app);
                ui.close_menu();
            }
        });

        // View Menu
        ui.menu_button("View", |ui| {
            if ui.button("Detailed View").clicked() {
                app.show_detailed_view = true;
                ui.close_menu();
            }
            if ui.button("Main View").clicked() {
                app.show_detailed_view = false;
                ui.close_menu();
            }
        });

        // Tools Menu
        ui.menu_button("Tools", |ui| {
            if ui.button("Import Local Skin").clicked() {
                app.show_import_popup = true;
                ui.close_menu();
            }
            if ui.button("Export Tags").clicked() {
                database_handlers::export_tags(app);
                ui.close_menu();
            }
            if ui.button("Import Tags").clicked() {
                database_handlers::import_tags(app);
                ui.close_menu();
            }
        });

        // Settings Menu
        ui.menu_button("Settings", |ui| {
            if ui.button("Custom Structure Settings").clicked() {
                app.show_custom_structure_popup = true;
                ui.close_menu();
            }
        });

        // Help Menu
        ui.menu_button("Help", |ui| {
            if ui.button("About").clicked() {
                app.show_about_popup = true;
                ui.close_menu();
            }
        });
    });
}

// Search bar function
pub fn search_bar(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        let search_bar = ui.text_edit_singleline(&mut app.search_query);
        if ui.button("🔍").clicked() || (search_bar.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter))) {
            general_handlers::perform_search(app);
        }
    });
}

// Tag filters function
pub fn tag_filters(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        ui.label("Filter by tags:");
        if ui.checkbox(&mut app.tag_filtering_enabled, "Enable Tag Filtering").changed() {
            if app.tag_filtering_enabled {
                app.selected_tags.clear();
            }
            general_handlers::perform_search(app);
        }
    });

    if app.tag_filtering_enabled {
        ui.horizontal(|ui| {
            let all_tags: Vec<_> = app.available_tags.iter().chain(app.custom_tags.iter()).cloned().collect();
            let mut tags_changed = false;

            for tag in all_tags {
                let mut is_selected = app.selected_tags.contains(&tag);
                if ui.checkbox(&mut is_selected, &tag).changed() {
                    if is_selected {
                        app.selected_tags.push(tag.clone());
                    } else {
                        app.selected_tags.retain(|t| t != &tag);
                    }
                    tags_changed = true;
                }
            }

            if tags_changed {
                general_handlers::perform_search(app);
            }
        });
    }

    if ui.button("Apply Filter").clicked() {
        general_handlers::perform_search(app);
    }
}

// Camouflage details function
pub fn camouflage_details(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    if let Some(camo) = &app.current_camo {
        ui.heading(&camo.vehicle_name);
        ui.label(&camo.description);
        ui.label(format!("File size: {}", camo.file_size));
        ui.label(format!("Posted on: {}", camo.post_date));
        ui.label(format!("Hashtags: {}", camo.hashtags.join(", ")));
        ui.label(format!("Tags: {}", camo.tags.join(", ")));
        ui.label(format!("Downloads: {}", camo.num_downloads));
        ui.label(format!("Likes: {}", camo.num_likes));
        ui.label(format!("Camouflage {}/{}", app.current_index + 1, app.total_camos));
    } else {
        ui.label("No camouflage selected");
    }
    if let Some(error) = &app.error_message {
        ui.label(error);
    }
}

// Pagination function
pub fn pagination(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        if ui.button("Previous").clicked() {
            navigation_handlers::show_previous_camo(app);
        }
        ui.label(format!("{}/{}", app.current_index + 1, app.total_camos));
        if ui.button("Next").clicked() {
            navigation_handlers::show_next_camo(app);
        }
    });
}

// Install button function
pub fn install_button(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    if let Some(camo) = &app.current_camo {
        let zip_file_url = camo.zip_file_url.clone();
        if ui.button("Install").clicked() {
            file_handlers::install_skin(app, &zip_file_url);
        }
    }
}

// Custom tags input function
pub fn custom_tags_input(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        ui.label("Custom Tags:");
        let input = ui.text_edit_singleline(&mut app.custom_tags_input);
        if ui.button("Add Tags").clicked() || (input.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter))) {
            general_handlers::add_custom_tags(app);
        }
    });
}

// Responsive image grid component
pub fn responsive_image_grid(
    ui: &mut egui::Ui,
    images: &HashMap<String, egui::TextureHandle>,
    image_urls: &[String],
    skip_first: bool,
) {
    let available_width = ui.available_width();
    let target_image_width = 200.0;
    let num_columns = (available_width / target_image_width).floor().max(1.0) as usize;

    egui::Grid::new("responsive_image_grid")
        .num_columns(num_columns)
        .spacing([10.0, 10.0])
        .show(ui, |ui| {
            for (index, url) in image_urls.iter().enumerate().skip(if skip_first { 1 } else { 0 }) {
                if let Some(texture_handle) = images.get(url) {
                    let size = texture_handle.size_vec2();
                    let aspect_ratio = size.x / size.y;
                    let image_width = available_width / num_columns as f32 - 10.0;
                    let image_height = image_width / aspect_ratio;
                    ui.image(texture_handle.id(), [image_width, image_height]);
                }
                if (index + 1) % num_columns == 0 {
                    ui.end_row();
                }
            }
        });
}

// Show image grid for detailed view
pub fn show_image_grid_for_detailed_view(ui: &mut egui::Ui, app: &WarThunderCamoInstaller) {
    if let Some(current_camo) = &app.current_camo {
        let images = app.images.lock().unwrap();
        if images.is_empty() {
            ui.label("No images to display.");
            return;
        }

        if let Some(avatar_url) = current_camo.image_urls.first() {
            if let Some(texture_handle) = images.get(avatar_url) {
                let size = texture_handle.size_vec2();
                ui.image(texture_handle.id(), size);
            }
        }

        ui.add_space(10.0);

        responsive_image_grid(ui, &images, &current_camo.image_urls, true);
    } else {
        ui.label("No camouflage selected.");
    }
}

// Show image grid for main view
pub fn show_image_grid_for_main_view(ui: &mut egui::Ui, app: &WarThunderCamoInstaller) {
    if let Some(current_camo) = &app.current_camo {
        let images = app.images.lock().unwrap();
        if images.is_empty() {
            ui.label("No images to display.");
            return;
        }

        if let Some(avatar_url) = current_camo.image_urls.first() {
            if let Some(texture_handle) = images.get(avatar_url) {
                let size = texture_handle.size_vec2();
                ui.image(texture_handle.id(), size);
            }
        }

        ui.add_space(10.0);

        responsive_image_grid(ui, &images, &current_camo.image_urls, true);
    } else {
        ui.label("No camouflage selected.");
    }
}
