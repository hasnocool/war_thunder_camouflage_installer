mod ui;
mod data;
mod database;
mod image_utils;
mod file_operations;
mod path_utils;
mod tags;
mod war_thunder_utils;

use eframe::{run_native, NativeOptions};
use ui::{initialize_handlers, WarThunderCamoInstaller};
use war_thunder_utils::find_war_thunder_directory;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let options = NativeOptions {
        initial_window_size: Some(egui::vec2(800.0, 600.0)),
        centered: true,
        ..Default::default()
    };

    println!("Starting War Thunder Camouflage Installer...");

    let mut installer = WarThunderCamoInstaller::new();
    initialize_handlers(&mut installer);

    // Try to find the War Thunder directory
    if let Some(wt_dir) = find_war_thunder_directory() {
        println!("War Thunder directory found: {}", wt_dir.display());
        installer.set_wt_skins_directory(&wt_dir.join("UserSkins"));
    } else {
        println!("War Thunder directory not found. Please set it manually.");
    }

    println!("Running application...");
    Ok(run_native(
        "War Thunder Camouflage Installer",
        options,
        Box::new(|_cc| Box::new(installer)),
    )?)
}
