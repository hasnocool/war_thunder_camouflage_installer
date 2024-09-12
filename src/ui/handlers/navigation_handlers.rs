use crate::ui::WarThunderCamoInstaller;

pub fn show_next_camo(app: &mut WarThunderCamoInstaller) {
    let total_camos = if app.search_mode {
        app.search_results.len()
    } else {
        app.total_camos
    };

    if total_camos == 0 {
        app.error_message = Some("No camouflages available.".to_string());
        return;
    }

    if app.current_index < total_camos - 1 {
        app.current_index += 1;
        let camo = if app.search_mode {
            app.search_results.get(app.current_index).cloned()
        } else {
            app.fetch_camouflage_by_index(app.current_index).ok().flatten().map(|(_, camo)| camo)
        };

        if let Some(camo) = camo {
            app.set_current_camo(app.current_index, camo);
        }
    } else {
        app.error_message = Some("Already at the last camouflage.".to_string());
    }
}

pub fn show_previous_camo(app: &mut WarThunderCamoInstaller) {
    if app.total_camos == 0 || app.current_index == 0 {
        app.error_message = Some("Already at the first camouflage.".to_string());
        return;
    }

    app.current_index -= 1;

    let camo = if app.search_mode {
        app.search_results.get(app.current_index).cloned()
    } else {
        app.fetch_camouflage_by_index(app.current_index).ok().flatten().map(|(_, camo)| camo)
    };

    if let Some(camo) = camo {
        app.set_current_camo(app.current_index, camo);
    }
}

