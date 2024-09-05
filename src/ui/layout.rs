// src/ui/layout.rs

use eframe::egui;
use super::app::WarThunderCamoInstaller;
use super::components;
use super::handlers;

pub fn build_ui(app: &mut WarThunderCamoInstaller, ctx: &egui::Context) {
    top_panel(app, ctx);
    central_panel(app, ctx);
    bottom_panel(app, ctx);
    show_popups(app, ctx);
}

fn top_panel(app: &mut WarThunderCamoInstaller, ctx: &egui::Context) {
    egui::TopBottomPanel::top("menu_bar").show(ctx, |ui| {
        components::menu_bar(app, ui);
    });

    egui::TopBottomPanel::top("header_panel").min_height(70.0).show(ctx, |ui| {
        components::search_bar(app, ui);
        components::tag_filters(app, ui); // Corrected to use components::tag_filters
    });
}

fn central_panel(app: &mut WarThunderCamoInstaller, ctx: &egui::Context) {
    egui::CentralPanel::default().show(ctx, |ui| {
        egui::ScrollArea::vertical().show(ui, |ui| {
            components::camouflage_details(app, ui);
        });
    });
}

fn bottom_panel(app: &mut WarThunderCamoInstaller, ctx: &egui::Context) {
    egui::TopBottomPanel::bottom("footer_panel").min_height(100.0).show(ctx, |ui| {
        components::pagination(app, ui);
        components::install_button(app, ui);
        components::custom_tags_input(app, ui);
    });
}

fn show_popups(app: &mut WarThunderCamoInstaller, ctx: &egui::Context) {
    handlers::show_custom_structure_popup(app, ctx);
    handlers::show_about_popup(app, ctx);
    handlers::show_import_popup(app, ctx);
}
