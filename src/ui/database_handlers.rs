use super::app::WarThunderCamoInstaller;
use crate::database;

// Function to update the total number of camouflages
pub fn update_total_camos(app: &mut WarThunderCamoInstaller) {
    if let Some(db_conn) = &app.db_conn {
        match database::update_total_camos(db_conn) {
            Ok(count) => app.total_camos = count,
            Err(e) => app.error_message = Some(format!("Failed to update total camos: {}", e)),
        }
    }
}

// Function to refresh available tags in the application
pub fn refresh_available_tags(app: &mut WarThunderCamoInstaller) {
    if let Some(db_conn) = &app.db_conn {
        match database::fetch_tags(db_conn, 0) {
            Ok(tags) => app.available_tags = tags,
            Err(e) => app.error_message = Some(format!("Failed to refresh available tags: {}", e)),
        }
    }
}

// Function to export tags to a JSON file
pub fn export_tags(app: &mut WarThunderCamoInstaller) {
    if let Some(path) = rfd::FileDialog::new()
        .add_filter("JSON", &["json"])
        .save_file()
    {
        match app.export_tags(&path) {
            Ok(_) => app.error_message = Some("Tags exported successfully".to_string()),
            Err(e) => app.error_message = Some(format!("Failed to export tags: {}", e)),
        }
    }
}

// Function to import tags from a JSON file
pub fn import_tags(app: &mut WarThunderCamoInstaller) {
    if let Some(path) = rfd::FileDialog::new()
        .add_filter("JSON", &["json"])
        .pick_file()
    {
        match app.import_tags(&path) {
            Ok(_) => app.error_message = Some("Tags imported successfully".to_string()),
            Err(e) => app.error_message = Some(format!("Failed to import tags: {}", e)),
        }
    }
}