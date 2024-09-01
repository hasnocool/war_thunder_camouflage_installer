use std::sync::mpsc::Sender;
use std::path::{Path, PathBuf};
use image::{codecs::png::PngEncoder, ImageEncoder, ImageError};

pub fn load_image(sender: Sender<(String, Vec<u8>)>, url: String, cache_dir: PathBuf) -> Result<(), ImageError> {
    println!("Attempting to load image from URL: {}", url);
    let filename = url.split('/').last().unwrap_or("default.png");
    let cache_path = cache_dir.join(filename);

    if cache_path.exists() {
        // Load image from cache
        if let Ok(image) = load_image_from_cache(&cache_path) {
            let _ = sender.send((url.clone(), image));
            println!("Successfully loaded and encoded image from cache: {:?}", cache_path);
            Ok(())
        } else {
            println!("Failed to load image from cache");
            Err(ImageError::IoError(std::io::Error::new(std::io::ErrorKind::Other, "Failed to load image from cache")))
        }
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

                        // Load the image and send it
                        if let Ok(image) = image::load_from_memory(&bytes) {
                            let mut buffer = Vec::new();
                            if PngEncoder::new(&mut buffer)
                                .write_image(
                                    image.to_rgba8().as_raw(),
                                    image.width(),
                                    image.height(),
                                    image::ColorType::Rgba8
                                )
                                .is_ok()
                            {
                                let _ = sender.send((url.clone(), buffer));
                                println!("Successfully loaded and encoded image from URL: {}", url);
                                Ok(())
                            } else {
                                println!("Failed to encode image from URL: {}", url);
                                Err(ImageError::IoError(std::io::Error::new(std::io::ErrorKind::Other, "Failed to encode image from URL")))
                            }
                        } else {
                            println!("Failed to load image from memory");
                            Err(ImageError::Decoding(image::error::DecodingError::new(
                                image::error::ImageFormatHint::Unknown, "Failed to load image from memory"
                            )))
                        }
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

pub fn load_image_from_cache(cache_path: &Path) -> Result<Vec<u8>, ImageError> {
    let image = image::open(cache_path)?;
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
    std::fs::write(cache_path, image_data)?;
    Ok(())
}

pub fn clear_cache(cache_dir: &Path) -> std::io::Result<()> {
    for entry in std::fs::read_dir(cache_dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.is_file() {
            std::fs::remove_file(path)?;
        }
    }
    println!("Cache cleared successfully");
    Ok(())
}