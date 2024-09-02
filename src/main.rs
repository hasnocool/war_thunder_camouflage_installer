mod data;
mod database;
mod image_utils;
mod file_operations;
mod path_utils;
mod ui;

use eframe::{run_native, NativeOptions};
use std::path::Path;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Set initial window options, including size and centering behavior
    let options = NativeOptions {
        initial_window_size: Some(egui::vec2(800.0, 600.0)), // Set desired initial window size
        centered: true, // Center the window on screen at startup
        ..Default::default()
    };

    let db_path = Path::new("war_thunder_camouflages.db");

    println!("Attempting to create WarThunderCamoInstaller...");

    match ui::WarThunderCamoInstaller::new(db_path) {
        Ok(installer) => {
            println!("Successfully created WarThunderCamoInstaller. Running application...");
            Ok(run_native(
                "War Thunder Camouflage Installer",
                options,
                Box::new(|_cc| Box::new(installer)),
            )?)
        },
        Err(e) => {
            eprintln!("Failed to initialize the application: {:?}", e);
            eprintln!("This could be due to database initialization issues.");
            eprintln!("Make sure you have write permissions in the directory containing: {:?}", db_path);
            Err(Box::new(e))
        }
    }
}