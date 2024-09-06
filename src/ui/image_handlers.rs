use eframe::egui;
use std::sync::mpsc;
use rayon::prelude::*;
use super::app::WarThunderCamoInstaller;
use crate::image_utils;
use image::GenericImageView; // Add this import

// Function to update the image grid with loaded images
pub fn update_image_grid(app: &WarThunderCamoInstaller, ctx: &egui::Context) {
    let mut loading = app.loading_images.lock().unwrap();
    if *loading {
        return;
    }

    let mut queue = app.image_load_queue.lock().unwrap();
    if queue.is_empty() {
        return;
    }

    *loading = true;
    let urls: Vec<String> = queue.drain(..).collect();
    let images = app.images.clone();
    let ctx = ctx.clone();
    let loading_images = app.loading_images.clone();

    std::thread::spawn(move || {
        let (tx, rx) = mpsc::channel();
        let tx = std::sync::Arc::new(std::sync::Mutex::new(tx));

        urls.par_iter().for_each_with(tx.clone(), |tx, url: &String| {
            if let Ok(image_data) = image_utils::load_image(url.clone()) {
                if let Ok(dynamic_image) = image::load_from_memory(&image_data) {
                    let (width, height) = dynamic_image.dimensions();
                    let rgba_image = dynamic_image.to_rgba8();
                    let image = egui::ColorImage::from_rgba_unmultiplied(
                        [width as usize, height as usize],
                        rgba_image.as_raw(),
                    );
                    let _ = tx.lock().unwrap().send((url.clone(), image));
                }
            }
        });

        drop(tx);

        for (url, image) in rx {
            ctx.request_repaint();
            let texture = ctx.load_texture(
                url.clone(),
                image,
                egui::TextureOptions::default(),
            );
            images.lock().unwrap().insert(url, texture);
        }

        *loading_images.lock().unwrap() = false;
    });
}

// Function to load the current camouflage's images
pub fn load_current_camo_images(app: &WarThunderCamoInstaller) {
    if let Some(camo) = &app.current_camo {
        let mut queue = app.image_load_queue.lock().unwrap();
        for url in &camo.image_urls {
            if !app.images.lock().unwrap().contains_key(url as &str) {
                queue.push_back(url.clone());
            }
        }
    }
}

// Function to clear the cache
pub fn clear_cache(app: &mut WarThunderCamoInstaller) {
    if let Err(e) = image_utils::clear_cache() {
        app.error_message = Some(format!("Failed to clear cache: {}", e));
    } else {
        app.error_message = Some("Cache cleared successfully".to_string());
    }
}