use crate::ui::WarThunderCamoInstaller;

// Modify the set_wt_skins_directory function to update the existing directory
pub fn set_wt_skins_directory(app: &mut WarThunderCamoInstaller) {
    // Only prompt when the user selects the option
    if let Some(path) = rfd::FileDialog::new().pick_folder() {
        app.set_wt_skins_directory(&path);
        app.error_message = Some(format!("Skins directory set to: {}", path.display()));
    } else {
        app.error_message = Some("No directory selected.".to_string());
    }
}



pub fn change_database_file(app: &mut WarThunderCamoInstaller) {
    // Only trigger when the user chooses to change the DB
    if let Some(path) = rfd::FileDialog::new()
        .add_filter("SQLite Database", &["db", "sqlite"])
        .pick_file()
    {
        if let Err(e) = app.initialize_database(&path) {
            app.error_message = Some(format!("Failed to change database: {}", e));
        } else {
            app.error_message = Some(format!("Database changed to: {}", path.display()));
        }
    }
}
// Function to perform search
pub fn perform_search(app: &mut WarThunderCamoInstaller) {
    let query = if app.search_query.is_empty() { None } else { Some(app.search_query.as_str()) };

    let selected_tags = if app.tag_filtering_enabled {
        &app.selected_tags
    } else {
        &Vec::new()
    };

    match app.fetch_camouflages(query, selected_tags) {
        Ok(results) => {
            app.search_results = results;
            app.search_mode = true;
            if !app.search_results.is_empty() {
                app.current_index = 0;
                app.set_current_camo(0, app.search_results[0].clone());
            } else {
                app.current_index = 0;
                app.current_camo = None;
                app.clear_images();
                app.error_message = Some("No results found".to_string());
            }
        }
        Err(e) => {
            app.error_message = Some(format!("Search error: {:?}", e));
            app.search_results.clear();
            app.current_camo = None;
            app.clear_images();
        }
    }
}

// Function to add custom tags input by the user
pub fn add_custom_tags(app: &mut WarThunderCamoInstaller) {
    let new_tags: Vec<String> = app.custom_tags_input
        .split(',')
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect();
    app.custom_tags.extend(new_tags);
    app.custom_tags.sort();
    app.custom_tags.dedup();
    app.custom_tags_input.clear();
}