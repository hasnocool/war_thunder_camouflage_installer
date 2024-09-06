// src/ui/layout.rs

use eframe::egui;
use super::app::WarThunderCamoInstaller;
use super::components;
use super::popup_handlers;

pub fn build_ui(app: &mut WarThunderCamoInstaller, ctx: &egui::Context) {
    top_panel(app, ctx);

    if app.show_detailed_view {
        detailed_view(app, ctx); // Show the detailed view layout
    } else {
        central_panel(app, ctx); // Show the main view layout
    }

    bottom_panel(app, ctx);
    show_popups(app, ctx);
}

fn detailed_view(app: &mut WarThunderCamoInstaller, ctx: &egui::Context) {
    let available_height = ctx.available_rect().height();
    let line_height = 30.0; // Approximate height of a line in the sidebar
    let items_per_page = (available_height / line_height).floor() as usize;

    let start_index = app.current_page * items_per_page;
    let end_index = (start_index + items_per_page).min(app.search_results.len());

    let camouflages_to_display: Vec<_> = app.search_results[start_index..end_index].to_vec();

    egui::SidePanel::left("sidebar_panel").show(ctx, |ui| {
        // Updated heading to show current camouflage index out of total
        ui.heading(format!(
            "Camouflages ({}/{})", 
            app.current_index + 1, 
            app.total_camos
        ));

        egui::ScrollArea::vertical().show(ui, |ui| {
            for (index, camo) in camouflages_to_display.iter().enumerate() {
                let global_index = start_index + index;
                if ui.selectable_label(app.current_index == global_index, &camo.vehicle_name).clicked() {
                    app.set_current_camo(global_index, camo.clone());
                }
            }
        });

        ui.separator();
        ui.horizontal(|ui| {
            // Handle pagination
            if ui.button("Previous").clicked() && app.current_page > 0 {
                app.current_page -= 1;
            }
            ui.label(format!(
                "Page {}/{}",
                app.current_page + 1,
                (app.search_results.len() + items_per_page - 1) / items_per_page
            ));
            if ui.button("Next").clicked() && end_index < app.search_results.len() {
                app.current_page += 1;
            }
        });

        // Add "Go to Index" feature
        ui.horizontal(|ui| {
            ui.label("Go to Index:");
            let mut input_index = app.current_index.to_string(); // Store the current index as a String for input
            if ui.text_edit_singleline(&mut input_index).lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter)) {
                // Check bounds and set the camouflage by the input index
                if let Ok(index) = input_index.parse::<usize>() {
                    if index < app.total_camos {
                        if let Some(camo) = app.search_results.get(index) {
                            app.set_current_camo(index, camo.clone());
                        }
                    }
                }
            }
        });
    });

    egui::CentralPanel::default().show(ctx, |ui| {
        egui::ScrollArea::vertical().id_source("detailed_panel_scroll").show(ui, |ui| {
            ui.heading("Camouflage Details");
            components::camouflage_details(app, ui);
            ui.add_space(20.0);
            ui.heading("Images");
            components::show_image_grid_for_detailed_view(ui, app);

            ui.horizontal(|ui| {
                if let Some(current_camo) = &app.current_camo {
                    let zip_url = current_camo.zip_file_url.clone(); // Clone the URL
                    if ui.button("Install Skin").clicked() {
                        app.start_skin_installation(&zip_url);
                    }
                } else {
                    ui.label("No camouflage selected.");
                }
            });
        });
    });
}

fn top_panel(app: &mut WarThunderCamoInstaller, ctx: &egui::Context) {
    egui::TopBottomPanel::top("menu_bar").show(ctx, |ui| {
        components::menu_bar(app, ui);
    });

    egui::TopBottomPanel::top("header_panel").min_height(70.0).show(ctx, |ui| {
        components::search_bar(app, ui);
        components::tag_filters(app, ui);
    });
}

fn central_panel(app: &mut WarThunderCamoInstaller, ctx: &egui::Context) {
    egui::CentralPanel::default().show(ctx, |ui| {
        egui::ScrollArea::vertical().id_source("central_panel_scroll").show(ui, |ui| {
            ui.heading("Camouflage Details");
            components::camouflage_details(app, ui);
            ui.add_space(20.0);
            ui.heading("Images");
            show_image_grid_for_main_view(ui, app);

            ui.horizontal(|ui| {
                if let Some(current_camo) = &app.current_camo {
                    let zip_url = current_camo.zip_file_url.clone();  // Clone the URL
                    if ui.button("Install Skin").clicked() {
                        app.start_skin_installation(&zip_url);  // Mutate app here
                    }
                } else {
                    ui.label("No camouflage selected.");
                }
            });
        });
    });
}

// Function to show the image grid in the main view
fn show_image_grid_for_main_view(ui: &mut egui::Ui, app: &WarThunderCamoInstaller) {
    if let Some(current_camo) = &app.current_camo {
        let images = app.images.lock().unwrap();
        if images.is_empty() {
            ui.label("No images to display.");
            return;
        }

        // Display the first image as the avatar
        if let Some(avatar_url) = current_camo.image_urls.get(0) {
            if let Some(texture_handle) = images.get(avatar_url) {
                let size = texture_handle.size_vec2();
                ui.image(texture_handle.id(), size);
            }
        }

        let available_width = ui.available_width();
        let image_width = 150.0;
        let num_columns = (available_width / image_width).floor() as usize;

        // Display the rest of the images (skip the avatar)
        egui::Grid::new("image_grid_for_main_view")
            .num_columns(num_columns)
            .spacing([10.0, 10.0])
            .striped(true)
            .show(ui, |ui| {
                for url in &current_camo.image_urls[1..] {
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

fn bottom_panel(app: &mut WarThunderCamoInstaller, ctx: &egui::Context) {
    egui::TopBottomPanel::bottom("footer_panel").min_height(100.0).show(ctx, |ui| {
        components::pagination(app, ui);
        components::install_button(app, ui);
        components::custom_tags_input(app, ui);
    });
}

fn show_popups(app: &mut WarThunderCamoInstaller, ctx: &egui::Context) {
    popup_handlers::show_custom_structure_popup(app, ctx);
    popup_handlers::show_about_popup(app, ctx);
    popup_handlers::show_import_popup(app, ctx);
}