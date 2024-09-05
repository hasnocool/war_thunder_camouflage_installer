use eframe::egui;
use super::app::WarThunderCamoInstaller;
use super::handlers;

pub fn menu_bar(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    egui::menu::bar(ui, |ui| {
        ui.menu_button("File", |ui| {
            if ui.button("Set War Thunder Skins Directory").clicked() {
                handlers::set_wt_skins_directory(app);
                ui.close_menu();
            }
            if ui.button("Set Database File").clicked() {
                handlers::select_database_file(app);
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
                handlers::export_tags(app);
                ui.close_menu();
            }
            if ui.button("Import Tags").clicked() {
                handlers::import_tags(app);
                ui.close_menu();
            }
            if ui.button("Clear Cache").clicked() {
                handlers::clear_cache(app);
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
            handlers::perform_search(app);
        }
    });
}

pub fn tag_filters(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        ui.label("Filter by tags:");
        let all_tags: Vec<_> = app.available_tags.iter().chain(app.custom_tags.iter()).collect();
        for tag in all_tags {
            let mut is_selected = app.selected_tags.contains(tag);
            if ui.checkbox(&mut is_selected, tag).clicked() {
                if is_selected {
                    app.selected_tags.push(tag.to_string());
                } else {
                    app.selected_tags.retain(|t| t != tag);
                }
            }
        }
        if ui.button("Apply Filter").clicked() {
            handlers::perform_search(app);
        }
    });
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
        show_image_grid(app, ui);
    } else {
        ui.label("No camouflage selected");
        if let Some(error) = &app.error_message {
            ui.label(error);
        }
    }
}

pub fn show_image_grid(app: &WarThunderCamoInstaller, ui: &mut egui::Ui) {
    let images = app.images.lock().unwrap();
    if images.is_empty() {
        ui.label("No images to display.");
        return;
    }

    let available_width = ui.available_width();
    let image_width = 150.0;
    let num_columns = (available_width / image_width).floor() as usize;

    egui::Grid::new("image_grid")
        .num_columns(num_columns)
        .spacing([10.0, 10.0])
        .striped(true)
        .show(ui, |ui| {
            for (_, texture_handle) in images.iter() {
                let size = texture_handle.size_vec2();
                let aspect_ratio = size.x / size.y;
                let scaled_height = image_width / aspect_ratio;
                ui.image(texture_handle.id(), [image_width, scaled_height]);
            }
        });
}

pub fn pagination(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        if ui.button("Previous").clicked() {
            handlers::show_previous_camo(app);
        }
        ui.label(format!("{}/{}", app.current_index + 1, if app.search_mode { app.search_results.len() } else { app.total_camos }));
        if ui.button("Next").clicked() {
            handlers::show_next_camo(app);
        }
    });
}

pub fn install_button(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    if let Some(camo) = &app.current_camo {
        let zip_file_url = camo.zip_file_url.clone();
        if ui.button("Install").clicked() {
            handlers::install_skin(app, &zip_file_url);
        }
    }
}

pub fn custom_tags_input(app: &mut WarThunderCamoInstaller, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        ui.label("Custom Tags:");
        let input = ui.text_edit_singleline(&mut app.custom_tags_input);
        if ui.button("Add Tags").clicked() || (input.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter))) {
            handlers::add_custom_tags(app);
        }
    });
}