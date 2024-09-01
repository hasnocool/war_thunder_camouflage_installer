mod data;
mod database;
mod image_utils;
mod file_operations;
mod path_utils;
mod ui;

use eframe::{run_native, NativeOptions};
use std::path::Path;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let options = NativeOptions::default();
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
            eprintln!("Make sure the database file exists at: {:?}", db_path);
            Err(Box::new(e))
        }
    }
}