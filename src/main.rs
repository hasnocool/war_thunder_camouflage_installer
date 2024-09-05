use eframe::{run_native, NativeOptions};
use std::path::Path;
use std::env;

mod ui; // Add this line to import the `ui` module or crate

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let options = NativeOptions {
        initial_window_size: Some(egui::vec2(800.0, 600.0)),
        centered: true,
        ..Default::default()
    };

    let current_dir = env::current_dir()?;
    let db_path = current_dir.join("war_thunder_camouflages.db");

    println!("Attempting to create WarThunderCamoInstaller...");

    match ui::WarThunderCamoInstaller::new(&db_path) {
        Ok(installer) => {
            println!("Successfully created WarThunderCamoInstaller. Running application...");
            Ok(run_native(
                "War Thunder Camouflage Installer",
                options,
                Box::new(|_cc| Box::new(installer)),
            )?)
        },
        Err(e) => {
            eprintln!("Failed to initialize the application with the database: {:?}", e);
            eprintln!("Continuing without a database. Some features may be limited.");
            
            // Create an installer without a database
            let installer = ui::WarThunderCamoInstaller::new_without_db();
            
            Ok(run_native(
                "War Thunder Camouflage Installer",
                options,
                Box::new(|_cc| Box::new(installer)),
            )?)
        }
    }
}