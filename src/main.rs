use eframe::egui;
use rusqlite::{Connection, Result};
use std::path::{Path, PathBuf};
use std::sync::mpsc::{channel, Receiver, Sender, TryRecvError};
use std::thread;
use image::{codecs::png::PngEncoder, ImageEncoder};
use rfd::FileDialog;
use reqwest;
use tempfile::Builder;
use std::collections::HashMap;

#[derive(Clone, Debug)]
struct Camouflage {
    vehicle_name: String,
    description: String,
    image_urls: Vec<String>,
    zip_file_url: String,
    hashtags: Vec<String>,
    file_size: String,
    num_downloads: i32,
    num_likes: i32,
    post_date: String,
}

struct WarThunderCamoInstaller {
    db_conn: Connection,
    current_camo: Option<Camouflage>,
    image_receiver: Receiver<(String, Vec<u8>)>,
    image_sender: Sender<(String, Vec<u8>)>,
    images: HashMap<String, egui::TextureHandle>,
    error_message: Option<String>,
    search_query: String,
    current_index: usize,
    total_camos: usize,
    loading_images: bool,
    is_initial_view: bool,
    wt_skins_dir: Option<PathBuf>,
}

impl WarThunderCamoInstaller {
    fn new(db_path: &Path) -> Result<Self> {
        println!("Attempting to open database at: {:?}", db_path);
        let db_conn = Connection::open(db_path)?;
        let (image_sender, image_receiver) = channel();
        let mut installer = Self {
            db_conn,
            current_camo: None,
            image_receiver,
            image_sender,
            images: HashMap::new(),
            error_message: None,
            search_query: String::new(),
            current_index: 0,
            total_camos: 0,
            loading_images: false,
            is_initial_view: true,
            wt_skins_dir: None,
        };
        installer.update_total_camos()?;
        Ok(installer)
    }

    fn update_total_camos(&mut self) -> Result<()> {
        let count: i64 = self.db_conn.query_row(
            "SELECT COUNT(*) FROM camouflages",
            [],
            |row| row.get(0),
        )?;
        self.total_camos = count as usize;
        Ok(())
    }

    fn fetch_camouflage(&mut self, index: usize) -> Result<Option<Camouflage>> {
        let mut stmt = self.db_conn.prepare(
            "SELECT vehicle_name, description, image_urls, zip_file_url, hashtags, file_size, num_downloads, num_likes, post_date 
            FROM camouflages 
            LIMIT 1 OFFSET ?"
        )?;
        
        let camo_iter = stmt.query_map([index], |row| {
            Ok(Camouflage {
                vehicle_name: row.get(0)?,
                description: row.get(1)?,
                image_urls: row.get::<_, Option<String>>(2)?
                    .unwrap_or_default()
                    .split(',')
                    .map(String::from)
                    .collect(),
                zip_file_url: row.get(3)?,
                hashtags: row.get::<_, Option<String>>(4)?
                    .unwrap_or_default()
                    .split(',')
                    .map(String::from)
                    .filter(|s| !s.is_empty())
                    .collect(),
                file_size: row.get(5)?,
                num_downloads: row.get(6)?,
                num_likes: row.get(7)?,
                post_date: row.get(8)?,
            })
        })?;

        let camo = camo_iter.collect::<Result<Vec<_>>>()?.into_iter().next();
        if camo.is_some() {
            self.current_index = index;
        }
        Ok(camo)
    }

    fn set_current_camo(&mut self, camo: Camouflage) {
        self.current_camo = Some(camo);
        self.load_current_camo_images();
    }

    fn load_current_camo_images(&mut self) {
        if let Some(camo) = &self.current_camo {
            self.loading_images = true;
            for url in &camo.image_urls {
                if !self.images.contains_key(url) {
                    // Load images in parallel using threads
                    let sender_clone = self.image_sender.clone();
                    let url_clone = url.clone();
                    thread::spawn(move || {
                        WarThunderCamoInstaller::load_image(sender_clone, url_clone);
                    });
                }
            }
        }
    }

    fn load_image(sender: Sender<(String, Vec<u8>)>, url: String) {
        println!("Attempting to load image from URL: {}", url);
        let url_clone = url.clone();
        match reqwest::blocking::get(&url) {
            Ok(response) => {
                match image::load_from_memory(&response.bytes().unwrap()) {
                    Ok(image) => {
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
                            let _ = sender.send((url_clone.clone(), buffer));
                            println!("Successfully loaded and encoded image from URL: {}", url_clone);
                        } else {
                            println!("Failed to encode image from URL: {}", url_clone);
                        }
                    },
                    Err(e) => println!("Failed to load image from memory: {}", e),
                }
            },
            Err(e) => println!("Failed to fetch image from URL: {}", e),
        }
    }

    fn install_skin(&self, zip_url: &str) -> Result<(), Box<dyn std::error::Error>> {
        if let Some(skins_directory) = &self.wt_skins_dir {
            println!("Downloading skin from {}", zip_url);
            let response = reqwest::blocking::get(zip_url)?;
            let zip_content = response.bytes()?;

            let temp_dir = Builder::new().prefix("wt_skin_").tempdir()?;
            let zip_path = temp_dir.path().join("skin.zip");
            std::fs::write(&zip_path, &zip_content)?;

            println!("Unzipping skin to {}", skins_directory.display());
            let file = std::fs::File::open(&zip_path)?;
            let mut archive = zip::ZipArchive::new(file)?;

            for i in 0..archive.len() {
                let mut file = archive.by_index(i)?;
                let outpath = skins_directory.join(file.mangled_name());

                if (&*file.name()).ends_with('/') {
                    std::fs::create_dir_all(&outpath)?;
                } else {
                    if let Some(p) = outpath.parent() {
                        if !p.exists() {
                            std::fs::create_dir_all(p)?;
                        }
                    }
                    let mut outfile = std::fs::File::create(&outpath)?;
                    std::io::copy(&mut file, &mut outfile)?;
                }
            }

            temp_dir.close()?;
            println!("Skin installed successfully!");
            Ok(())
        } else {
            Err("War Thunder skins directory not selected".into())
        }
    }

    fn perform_search(&mut self) {
        match self.search_camouflages(&self.search_query) {
            Ok(Some((index, camo))) => {
                self.current_index = index;
                self.set_current_camo(camo);
                self.error_message = None;
            }
            Ok(None) => {
                self.error_message = Some("No results found".to_string());
            }
            Err(e) => {
                self.error_message = Some(format!("Search error: {}", e));
            }
        }
    }

    fn search_camouflages(&self, query: &str) -> Result<Option<(usize, Camouflage)>> {
        let query = query.to_lowercase();
        let words: Vec<&str> = query.split_whitespace().collect();
        
        let mut sql = String::from(
            "SELECT rowid, vehicle_name, description, image_urls, zip_file_url, hashtags, file_size, num_downloads, num_likes, post_date 
            FROM camouflages 
            WHERE "
        );

        let mut conditions = Vec::new();
        let mut params = Vec::new();

        for word in &words {
            conditions.push("(LOWER(vehicle_name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(hashtags) LIKE ?)");
            params.push(format!("%{}%", word));
            params.push(format!("%{}%", word));
            params.push(format!("%{}%", word));
        }

        sql.push_str(&conditions.join(" AND "));
        sql.push_str(" LIMIT 1");

        let mut stmt = self.db_conn.prepare(&sql)?;
        
        let camo_iter = stmt.query_map(rusqlite::params_from_iter(params.iter()), |row| {
            let index: usize = row.get(0)?;
            Ok((index - 1, Camouflage {
                vehicle_name: row.get(1)?,
                description: row.get(2)?,
                image_urls: row.get::<_, Option<String>>(3)?
                    .unwrap_or_default()
                    .split(',')
                    .map(String::from)
                    .collect(),
                zip_file_url: row.get(4)?,
                hashtags: row.get::<_, Option<String>>(5)?
                    .unwrap_or_default()
                    .split(',')
                    .map(String::from)
                    .filter(|s| !s.is_empty())
                    .collect(),
                file_size: row.get(6)?,
                num_downloads: row.get(7)?,
                num_likes: row.get(8)?,
                post_date: row.get(9)?,
            }))
        })?;

        Ok(camo_iter.collect::<Result<Vec<_>>>()?.into_iter().next())
    }
}

impl eframe::App for WarThunderCamoInstaller {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        loop {
            match self.image_receiver.try_recv() {
                Ok((url, image_data)) => {
                    if let Ok(image) = image::load_from_memory(&image_data) {
                        let size = [image.width() as _, image.height() as _];
                        let image_buffer = image.to_rgba8();
                        let pixels = image_buffer.as_flat_samples();
                        let texture = ctx.load_texture(
                            &url,
                            egui::ColorImage::from_rgba_unmultiplied(size, pixels.as_slice()),
                            egui::TextureOptions::default(),
                        );
                        self.images.insert(url, texture);
                    }
                },
                Err(TryRecvError::Empty) => {
                    self.loading_images = false;
                    break;
                },
                Err(TryRecvError::Disconnected) => {
                    println!("Image receiver disconnected");
                    self.loading_images = false;
                    break;
                },
            }
        }

        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("War Thunder Camouflage Installer");

            ui.horizontal(|ui| {
                ui.label("Search:");
                let response = ui.text_edit_singleline(&mut self.search_query);
                if ui.button("Search").clicked() || (response.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter))) {
                    self.perform_search();
                }
            });

            if let Some(error) = &self.error_message {
                ui.colored_label(egui::Color32::RED, error);
            }

            ui.horizontal(|ui| {
                ui.label("War Thunder skins directory:");
                let mut skins_dir_string = self
                    .wt_skins_dir
                    .as_ref()
                    .map(|p| p.to_str().unwrap_or_default().to_string())
                    .unwrap_or_default();
                if ui.text_edit_singleline(&mut skins_dir_string).changed() {
                    self.wt_skins_dir = Some(PathBuf::from(skins_dir_string.clone()));
                }
                if ui.button("Browse").clicked() {
                    if let Some(path) = FileDialog::new().pick_folder() {
                        self.wt_skins_dir = Some(path);
                    }
                }
            });

            ui.horizontal(|ui| {
                if ui.button("Previous").clicked() && self.current_index > 0 {
                    if let Ok(Some(camo)) = self.fetch_camouflage(self.current_index - 1) {
                        self.set_current_camo(camo);
                    }
                }
                ui.label(format!("{}/{}", self.current_index + 1, self.total_camos));
                if ui.button("Next").clicked() && self.current_index < self.total_camos - 1 {
                    if let Ok(Some(camo)) = self.fetch_camouflage(self.current_index + 1) {
                        self.set_current_camo(camo);
                    }
                }
            });

            if let Some(camo) = &self.current_camo {
                let zip_file_url = camo.zip_file_url.clone();
                ui.heading(&camo.vehicle_name);
                ui.label(&camo.description);
                ui.label(format!("File size: {}", camo.file_size));
                ui.label(format!("Posted on: {}", camo.post_date));
                ui.label(format!("Hashtags: {}", camo.hashtags.join(", ")));
                ui.label(format!("Downloads: {}", camo.num_downloads));
                ui.label(format!("Likes: {}", camo.num_likes));

                if let Some(avatar_url) = camo.image_urls.first() {
                    if let Some(texture) = self.images.get(avatar_url) {
                        let size = texture.size_vec2();
                        ui.image(texture, size);
                    } else if self.loading_images {
                        ui.label("Loading avatar...");
                    }
                }

                ui.add_space(10.0);

                egui::ScrollArea::vertical().show(ui, |ui| {
                    ui.horizontal_wrapped(|ui| {
                        for url in camo.image_urls.iter().skip(1) {
                            if let Some(texture) = self.images.get(url) {
                                let size = texture.size_vec2();
                                let aspect_ratio = size.x / size.y;
                                let display_size = if self.is_initial_view {
                                    size
                                } else {
                                    let available_width = ui.available_width();
                                    let max_width = available_width.min(250.0);
                                    egui::vec2(max_width, max_width / aspect_ratio)
                                };
                                ui.add(egui::Image::new(texture, display_size));
                                ui.add_space(10.0);
                            } else if self.loading_images {
                                ui.add(egui::Spinner::new().size(32.0));
                                ui.add_space(10.0);
                            }
                        }
                    });
                });

                ui.horizontal(|ui| {
                    if ui.button("Install").clicked() {
                        if let Err(e) = self.install_skin(&zip_file_url) {
                            self.error_message = Some(format!("Failed to install skin: {}", e));
                        } else {
                            self.error_message = Some("Skin installed successfully!".to_string());
                        }
                    }
                });

                self.is_initial_view = false;
            } else {
                ui.label("No camouflage selected");
            }
        });

        if self.loading_images {
            ctx.request_repaint();
        }
    }
}

fn main() -> Result<(), eframe::Error> {
    let options = eframe::NativeOptions::default();
    let db_path = Path::new("war_thunder_camouflages.db");
    
    println!("Attempting to create WarThunderCamoInstaller...");
    match WarThunderCamoInstaller::new(db_path) {
        Ok(installer) => {
            println!("Successfully created WarThunderCamoInstaller. Running application...");
            eframe::run_native(
                "War Thunder Camouflage Installer",
                options,
                Box::new(|_cc| Box::new(installer)),
            )
        },
        Err(e) => {
            eprintln!("Failed to initialize the application: {}", e);
            eprintln!("Make sure the database file exists at: {:?}", db_path);
            Ok(())
        }
    }
}
