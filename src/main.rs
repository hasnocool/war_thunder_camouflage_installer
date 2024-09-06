mod ui;
mod data;
mod database;
mod image_utils;
mod file_operations;
mod path_utils;
mod tags;

use eframe::{run_native, NativeOptions};
use ui::{initialize_handlers, WarThunderCamoInstaller};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let options = NativeOptions {
        initial_window_size: Some(egui::vec2(800.0, 600.0)),
        centered: true,
        ..Default::default()
    };

    println!("Starting War Thunder Camouflage Installer...");

    let mut installer = WarThunderCamoInstaller::new();
    initialize_handlers(&mut installer);

    println!("Running application...");
    Ok(run_native(
        "War Thunder Camouflage Installer",
        options,
        Box::new(|_cc| Box::new(installer)),
    )?)
}