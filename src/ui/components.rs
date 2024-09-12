// src/ui/components.rs
use eframe::egui;
use super::app::WarThunderCamoInstaller;
use crate::ui::handlers::database_handlers;
use crate::ui::handlers::navigation_handlers;
use crate::ui::handlers::file_handlers;
use crate::ui::handlers::image_handlers;
use crate::ui::handlers::general_handlers;
use crate::ui::handlers::general_handlers::set_wt_skins_directory;
use crate::ui::handlers::general_handlers::change_database_file;


pub fn menu_bar(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    egui::menu::bar(ui, |ui| {
        ui.menu_button("File", |ui| {
            if ui.button("Change War Thunder Skins Directory").clicked() {
                set_wt_skins_directory(app);  // Call the method here
                ui.close_menu();
            }
            if ui.button("Change Database File").clicked() {
                change_database_file(app);
                ui.close_menu();
            }
            if ui.button("Custom Structure Settings").clicked() {
                app.show_custom_structure_popup = true;
                ui.close_menu();
            }
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
            if ui.button("Clear Cache").clicked() {
                image_handlers::clear_cache(app);
                ui.close_menu();
            }
        });

        ui.menu_button("View", |ui| {
            if ui.button("Detailed View").clicked() {
                app.show_detailed_view = true; // New field in app state to toggle detailed view
                ui.close_menu();
            }
            if ui.button("Main View").clicked() {
                app.show_detailed_view = false;
                ui.close_menu();
            }
        });

        ui.menu_button("About", |ui| {
            if ui.button("About").clicked() {
                app.show_about_popup = true;
                ui.close_menu();
            }
        });
    });
}


pub fn search_bar(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        let search_bar = ui.text_edit_singleline(&mut app.search_query);
        if ui.button("🔍").clicked() || (search_bar.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter))) {
            general_handlers::perform_search(app);
        }
    });
}

// Replace the existing tag_filters function with this:
pub fn tag_filters(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        ui.label("Filter by tags:");
        if ui.checkbox(&mut app.tag_filtering_enabled, "Enable Tag Filtering").changed() {
            if app.tag_filtering_enabled {
                app.selected_tags.clear();  // Reset selected tags when enabling filtering
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
        // New line to show the current index of the camouflage
        ui.label(format!("Camouflage {}/{}", app.current_index + 1, app.total_camos));
    } else {
        ui.label("No camouflage selected");
    }
    if let Some(error) = &app.error_message {
        ui.label(error);
    }
}

pub fn pagination(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        if ui.button("Previous").clicked() {
            navigation_handlers::show_previous_camo(app);
        }
        // Display current index and total camos
        ui.label(format!("{}/{}", app.current_index + 1, app.total_camos));
        if ui.button("Next").clicked() {
            navigation_handlers::show_next_camo(app);
        }
    });
}

pub fn install_button(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    if let Some(camo) = &app.current_camo {
        let zip_file_url = camo.zip_file_url.clone();
        if ui.button("Install").clicked() {
            file_handlers::install_skin(app, &zip_file_url);
        }
    }
}

pub fn custom_tags_input(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        ui.label("Custom Tags:");
        let input = ui.text_edit_singleline(&mut app.custom_tags_input);
        if ui.button("Add Tags").clicked() || (input.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter))) {
            general_handlers::add_custom_tags(app);
        }
    });
}


pub fn show_image_grid_for_detailed_view(ui: &mut egui::Ui, app: &WarThunderCamoInstaller) {
    if let Some(current_camo) = &app.current_camo {
        let images = app.images.lock().unwrap();
        if images.is_empty() {
            ui.label("No images to display.");
            return;
        }

        // Display the first image as the avatar in original size
        if let Some(avatar_url) = current_camo.image_urls.first() {
            if let Some(texture_handle) = images.get(avatar_url) {
                let size = texture_handle.size_vec2();
                ui.image(texture_handle.id(), size);
            }
        }

        let available_width = ui.available_width();
        let image_width = 150.0;
        let num_columns = (available_width / image_width).floor() as usize;

        egui::Grid::new("image_grid_for_detailed_view")
            .num_columns(num_columns)
            .spacing([10.0, 10.0])
            .striped(true)
            .show(ui, |ui| {
                for url in &current_camo.image_urls[1..] { // Skip the avatar
                    if let Some(texture_handle) = images.get(url) {
                        let size = texture_handle.size_vec2();
                        let aspect_ratio = size.x / size.y;
                        let scaled_height = image_width / aspect_ratio;
                        ui.image(texture_handle.id(), [image_width, scaled_height]);
                    }
                }
            });
    } else {
        ui.label("No camouflage selected.");
    }
}