mod app;
mod components;
mod layout;
mod handlers;

pub use app::WarThunderCamoInstaller;

pub use handlers::general_handlers::{perform_search, add_custom_tags};
pub use handlers::database_handlers::{update_total_camos, refresh_available_tags};
pub use handlers::navigation_handlers::{show_next_camo, show_previous_camo};
pub use handlers::image_handlers::{update_image_grid, load_current_camo_images, clear_cache};
pub use handlers::file_handlers::apply_custom_structure;
pub use handlers::popup_handlers::{show_custom_structure_popup, show_about_popup, show_import_popup};
pub use handlers::utility_handlers::update_app_state;

// ... rest of the file remains the same

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

    // Removed unnecessary lines
    // set_wt_skins_directory(app);
    // change_database_file(app);
    // install_skin(app, "");
    
    show_custom_structure_popup(app, &egui::Context::default());
    show_about_popup(app, &egui::Context::default());
    show_import_popup(app, &egui::Context::default());

    // Optional: if needed for future usage
    // export_tags(app);
    // import_tags(app);
}