use super::app::WarThunderCamoInstaller;

pub fn show_next_camo(app: &mut WarThunderCamoInstaller) {
    // If no camouflages or search results are present, return early
    if app.total_camos == 0 || (app.search_mode && app.search_results.is_empty()) {
        app.error_message = Some("No camouflages available.".to_string());
        return;
    }

    if app.search_mode {
        if app.current_index < app.search_results.len() - 1 {
            app.current_index += 1;
            if let Some(camo) = app.search_results.get(app.current_index) {
                app.set_current_camo(app.current_index, camo.clone());
            }
        } else {
            app.error_message = Some("Already at the last camouflage.".to_string());
        }
    } else if app.current_index < app.total_camos - 1 {
        let next_index = app.current_index + 1;
        if let Ok(Some((index, camo))) = app.fetch_camouflage_by_index(next_index) {
            app.set_current_camo(index, camo);
        } else {
            app.error_message = Some("Failed to load the next camouflage.".to_string());
        }
    } else {
        app.error_message = Some("Already at the last camouflage.".to_string());
    }
}

pub fn show_previous_camo(app: &mut WarThunderCamoInstaller) {
    // If no camouflages or search results are present, return early
    if app.total_camos == 0 || (app.search_mode && app.search_results.is_empty()) {
        app.error_message = Some("No camouflages available.".to_string());
        return;
    }

    if app.current_index > 0 {
        app.current_index -= 1;
        if app.search_mode {
            if let Some(camo) = app.search_results.get(app.current_index) {
                app.set_current_camo(app.current_index, camo.clone());
            }
        } else {
            if let Ok(Some((index, camo))) = app.fetch_camouflage_by_index(app.current_index) {
                app.set_current_camo(index, camo);
            } else {
                app.error_message = Some("Failed to load the previous camouflage.".to_string());
            }
        }
    } else {
        app.error_message = Some("Already at the first camouflage.".to_string());
    }
}
