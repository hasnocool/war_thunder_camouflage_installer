mod app;
mod components;
mod layout;
mod handlers;
mod database_handlers;
mod navigation_handlers;
mod image_handlers;
mod file_handlers;
mod popup_handlers;
mod utility_handlers;

// Re-export the main app struct
pub use app::WarThunderCamoInstaller;

// Re-export specific functions from each module
pub use handlers::{perform_search, add_custom_tags};
pub use database_handlers::{update_total_camos, refresh_available_tags};
pub use navigation_handlers::{show_next_camo, show_previous_camo};
pub use image_handlers::{update_image_grid, load_current_camo_images, clear_cache};
pub use file_handlers::{apply_custom_structure};
pub use popup_handlers::{show_custom_structure_popup, show_about_popup, show_import_popup};
pub use utility_handlers::update_app_state;

// Updated function to initialize all handlers
pub fn initialize_handlers(app: &mut WarThunderCamoInstaller) {
    perform_search(app);
    add_custom_tags(app);
    update_total_camos(app);
    refresh_available_tags(app);
    show_next_camo(app);
    show_previous_camo(app);
    update_image_grid(app, &egui::Context::default());
    load_current_camo_images(app);
    apply_custom_structure(app);
    update_app_state(app);
    clear_cache(app);
    // Remove the following lines:
    // set_wt_skins_directory(app);
    // change_database_file(app);
    // install_skin(app, "");
    show_custom_structure_popup(app, &egui::Context::default());
    show_about_popup(app, &egui::Context::default());
    show_import_popup(app, &egui::Context::default());
    //export_tags(app);
    //import_tags(app);
    
}