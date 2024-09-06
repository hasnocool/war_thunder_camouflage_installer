use super::app::WarThunderCamoInstaller;
use super::database_handlers;

// Helper function to update the application state
pub fn update_app_state(app: &mut WarThunderCamoInstaller) {
    database_handlers::update_total_camos(app);
    database_handlers::refresh_available_tags(app);
}