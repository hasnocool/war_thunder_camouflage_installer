use std::path::{Path, PathBuf};
use image::{codecs::png::PngEncoder, ImageEncoder, ImageError};
use std::fs;


pub fn get_cache_dir() -> PathBuf {
    let cache_dir = dirs::cache_dir()
        .unwrap_or_else(|| dirs::home_dir().expect("Unable to find home directory"))
        .join("war_thunder_camo_installer");

    if !cache_dir.exists() {
        fs::create_dir_all(&cache_dir).expect("Failed to create cache directory");
    }

    cache_dir
}

pub fn load_image(url: String) -> Result<Vec<u8>, ImageError> {
    println!("Attempting to load image from URL: {}", url);
    let filename = url.split('/').last().unwrap_or("default.png");
    let cache_dir = get_cache_dir();
    let cache_path = cache_dir.join(filename);

    if cache_path.exists() {
        // Load image from cache
        load_image_from_cache(&cache_path)
    } else {
        // Load image from URL
        match reqwest::blocking::get(&url) {
            Ok(response) => {
                match response.bytes() {
                    Ok(bytes) => {
                        // Save the image to cache
                        if let Err(e) = cache_image(&cache_path, &bytes) {
                            println!("Failed to save image to cache: {}", e);
                        } else {
                            println!("Image saved to cache: {:?}", cache_path);
                        }

                        // Load the image and return it
                        encode_image(&bytes)
                    },
                    Err(e) => {
                        println!("Failed to get image bytes: {}", e);
                        Err(ImageError::IoError(std::io::Error::new(std::io::ErrorKind::Other, "Failed to get image bytes")))
                    },
                }
            },
            Err(e) => {
                println!("Failed to fetch image from URL: {}", e);
                Err(ImageError::IoError(std::io::Error::new(std::io::ErrorKind::Other, "Failed to fetch image from URL")))
            },
        }
    }
}

fn load_image_from_cache(cache_path: &Path) -> Result<Vec<u8>, ImageError> {
    fs::read(cache_path).map_err(ImageError::IoError)
}

fn encode_image(image_data: &[u8]) -> Result<Vec<u8>, ImageError> {
    let image = image::load_from_memory(image_data)?;
    let mut buffer = Vec::new();
    PngEncoder::new(&mut buffer)
        .write_image(
            image.to_rgba8().as_raw(),
            image.width(),
            image.height(),
            image::ColorType::Rgba8
        )?;
    Ok(buffer)
}

pub fn cache_image(cache_path: &Path, image_data: &[u8]) -> std::io::Result<()> {
    fs::write(cache_path, image_data)
}

pub fn clear_cache() -> std::io::Result<()> {
    let cache_dir = get_cache_dir();
    for entry in fs::read_dir(cache_dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.is_file() {
            fs::remove_file(path)?;
        }
    }
    println!("Cache cleared successfully");
    Ok(())
}