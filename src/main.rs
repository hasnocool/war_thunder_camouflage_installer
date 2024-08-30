use eframe::egui;
use rusqlite::{Connection, Result};
use std::path::{Path, PathBuf};
use std::sync::mpsc::{channel, Receiver, Sender, TryRecvError};
use std::thread;
use image::{codecs::png::PngEncoder, ImageEncoder};
use rfd::FileDialog;
use reqwest;
use std::collections::HashMap;
use std::fs;
use std::io;
use zip::ZipArchive;

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
    nickname: String,
}

#[derive(thiserror::Error, Debug)]
enum InstallerError {
    #[error("SQLite error: {0}")]
    SqliteError(#[from] rusqlite::Error),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

struct WarThunderCamoInstaller {
    db_conn: Connection,
    current_camo: Option<Camouflage>,
    image_receiver: Receiver<(String, Vec<u8>)>,
    image_sender: Sender<(String, Vec<u8>)>,
    install_receiver: Receiver<Result<(), String>>,
    install_sender: Sender<Result<(), String>>,
    images: HashMap<String, egui::TextureHandle>,
    error_message: Option<String>,
    search_query: String,
    current_index: usize,
    total_camos: usize,
    loading_images: bool,
    is_initial_view: bool,
    wt_skins_dir: Option<PathBuf>,
    custom_structure: String,
    use_custom_structure: bool,
    show_import_popup: bool,
    show_about_popup: bool,  // Field for managing About popup
    cache_dir: PathBuf,
    selected_import_dir: Option<PathBuf>, // Field for storing the selected directory
    avatar_texture: Option<egui::TextureHandle>, // Field to store the avatar texture
}

impl WarThunderCamoInstaller {
    fn new(db_path: &Path) -> Result<Self, InstallerError> {
        println!("Attempting to open database at: {:?}", db_path);
        let db_conn = Connection::open(db_path)?;
        let (image_sender, image_receiver) = channel();
        let (install_sender, install_receiver) = channel();

        let cache_dir = PathBuf::from("cache");
        if !cache_dir.exists() {
            fs::create_dir_all(&cache_dir)?;
        }

        let mut installer = Self {
            db_conn,
            current_camo: None,
            image_receiver,
            image_sender,
            install_receiver,
            install_sender,
            images: HashMap::new(),
            error_message: None,
            search_query: String::new(),
            current_index: 0,
            total_camos: 0,
            loading_images: false,
            is_initial_view: true,
            wt_skins_dir: None,
            custom_structure: "%USERSKINS/%NICKNAME/%SKIN_NAME - %VEHICLE".to_string(),
            use_custom_structure: true,
            show_import_popup: false,
            show_about_popup: false,  // Initialize with false
            cache_dir,
            selected_import_dir: None, // Initialize with None
            avatar_texture: None, // Initialize with None
        };
        installer.update_total_camos()?;
        Ok(installer)
    }

    fn update_total_camos(&mut self) -> Result<(), InstallerError> {
        let count: i64 = self.db_conn.query_row(
            "SELECT COUNT(*) FROM camouflages",
            [],
            |row| row.get(0),
        )?;
        self.total_camos = count as usize;
        Ok(())
    }

    fn fetch_camouflage(&mut self, index: usize) -> Result<Option<Camouflage>, InstallerError> {
        let mut stmt = self.db_conn.prepare(
            "SELECT vehicle_name, description, image_urls, zip_file_url, hashtags, file_size, num_downloads, num_likes, post_date, nickname 
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
                nickname: row.get(9)?,
            })
        })?;
    
        let camo = camo_iter.collect::<Result<Vec<_>, rusqlite::Error>>()?.into_iter().next();
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
                    let sender_clone = self.image_sender.clone();
                    let url_clone = url.clone();
                    let cache_dir = self.cache_dir.clone();
                    thread::spawn(move || {
                        WarThunderCamoInstaller::load_image(sender_clone, url_clone, cache_dir);
                    });
                }
            }
        }
    }

    fn load_image(sender: Sender<(String, Vec<u8>)>, url: String, cache_dir: PathBuf) {
        println!("Attempting to load image from URL: {}", url);
        let filename = url.split('/').last().unwrap_or("default.png");
        let cache_path = cache_dir.join(filename);

        if cache_path.exists() {
            println!("Loading image from cache: {:?}", cache_path);
            if let Ok(image) = image::open(&cache_path) {
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
                    println!("Successfully loaded and encoded image from cache: {:?}", cache_path);
                }
            }
        } else {
            match reqwest::blocking::get(&url) {
                Ok(response) => {
                    match response.bytes() {
                        Ok(bytes) => {
                            // Save the image to cache
                            if let Err(e) = std::fs::write(&cache_path, &bytes) {
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
                                } else {
                                    println!("Failed to encode image from URL: {}", url);
                                }
                            } else {
                                println!("Failed to load image from memory");
                            }
                        },
                        Err(e) => println!("Failed to get image bytes: {}", e),
                    }
                },
                Err(e) => println!("Failed to fetch image from URL: {}", e),
            }
        }
    }

    fn clear_cache(&self) -> std::io::Result<()> {
        for entry in std::fs::read_dir(&self.cache_dir)? {
            let entry = entry?;
            let path = entry.path();
            if path.is_file() {
                std::fs::remove_file(path)?;
            }
        }
        println!("Cache cleared successfully");
        Ok(())
    }

    fn install_skin(&mut self, zip_url: &str) {
        if let Some(skins_directory) = &self.wt_skins_dir {
            println!("Downloading skin from {}", zip_url);
            let zip_url = zip_url.to_string();
            let skins_directory = skins_directory.clone();
            let custom_structure = self.custom_structure.clone();
            let current_camo = self.current_camo.clone().unwrap();
            let install_sender = self.install_sender.clone();
            let use_custom_structure = self.use_custom_structure;
            let cache_dir = self.cache_dir.clone();

            thread::spawn(move || {
                let result = WarThunderCamoInstaller::download_and_extract_skin(zip_url, skins_directory, custom_structure, &current_camo, use_custom_structure, cache_dir);
                let _ = install_sender.send(result.map_err(|e| e.to_string()));
            });
        } else {
            self.error_message = Some("War Thunder skins directory not selected".to_string());
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
                self.error_message = Some(format!("Search error: {:?}", e));
            }
        }
    }

    fn search_camouflages(&self, query: &str) -> Result<Option<(usize, Camouflage)>, InstallerError> {
        let query = query.to_lowercase();
        let words: Vec<&str> = query.split_whitespace().collect();
        
        let mut sql = String::from(
            "SELECT rowid, vehicle_name, description, image_urls, zip_file_url, hashtags, file_size, num_downloads, num_likes, post_date, nickname
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
                nickname: row.get(10)?,
            }))
        })?;

        Ok(camo_iter.collect::<Result<Vec<_>, rusqlite::Error>>()?.into_iter().next())
    }

    fn download_and_extract_skin(
        zip_url: String,
        skins_directory: PathBuf,
        custom_structure: String,
        camo: &Camouflage,
        use_custom_structure: bool,
        cache_dir: PathBuf,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let filename = zip_url.split('/').last().unwrap_or("default.zip");
        let cache_path = cache_dir.join(filename);

        if cache_path.exists() {
            println!("Using cached zip file: {:?}", cache_path);
        } else {
            let response = reqwest::blocking::get(&zip_url)?;
            let zip_content = response.bytes()?;
            std::fs::write(&cache_path, &zip_content)?;
        }

        println!("Unzipping skin to appropriate directory structure");
        let file = std::fs::File::open(&cache_path)?;
        let mut archive = zip::ZipArchive::new(file)?;

        let out_dir = if use_custom_structure {
            WarThunderCamoInstaller::generate_custom_path(&skins_directory, &custom_structure, camo)
        } else {
            skins_directory.join(&camo.vehicle_name)
        };
        std::fs::create_dir_all(&out_dir)?;

        for i in 0..archive.len() {
            let mut file = archive.by_index(i)?;
            let outpath = out_dir.join(file.mangled_name());

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

        Ok(())
    }

    fn generate_custom_path(base_dir: &PathBuf, custom_structure: &str, camo: &Camouflage) -> PathBuf {
        let mut path = custom_structure.to_string();
        path = path.replace("%USERSKINS", base_dir.to_str().unwrap());
        path = path.replace("%NICKNAME", &camo.nickname);
        path = path.replace("%SKIN_NAME", &camo.vehicle_name);
        path = path.replace("%VEHICLE", &camo.vehicle_name);

        PathBuf::from(path)
    }

    // Load avatar image from assets
    fn load_avatar_image(&mut self, ctx: &egui::Context) {
        let avatar_path = Path::new("assets/avatar.jpg");
        if avatar_path.exists() {
            if let Ok(image) = image::open(avatar_path) {
                let size = [image.width() as _, image.height() as _];
                let image_buffer = image.to_rgba8();
                let pixels = image_buffer.as_flat_samples();
                let texture = ctx.load_texture(
                    "avatar",
                    egui::ColorImage::from_rgba_unmultiplied(size, pixels.as_slice()),
                    egui::TextureOptions::default(),
                );
                self.avatar_texture = Some(texture);
            }
        }
    }
}

// Updated global function for importing skins
fn import_local_skin(
    _skins_directory: &PathBuf,  // Prefix with an underscore to suppress the warning
    selected_import_dir: &PathBuf,
) -> Result<(), Box<dyn std::error::Error>> {
    let file_path = FileDialog::new()
        .add_filter("Archive", &["zip", "rar"])
        .pick_file()
        .ok_or("No file selected for import")?;

    println!("Importing skin from {:?}", file_path);
    let file = fs::File::open(&file_path)?;
    let mut archive = ZipArchive::new(file)?;

    let out_dir = selected_import_dir.clone(); // Use the selected directory

    fs::create_dir_all(&out_dir)?;

    for i in 0..archive.len() {
        let mut file = archive.by_index(i)?;
        let outpath = out_dir.join(file.mangled_name());

        if file.name().ends_with('/') {
            fs::create_dir_all(&outpath)?;
        } else {
            if let Some(p) = outpath.parent() {
                if !p.exists() {
                    fs::create_dir_all(p)?;
                }
            }
            let mut outfile = fs::File::create(&outpath)?;
            io::copy(&mut file, &mut outfile)?;
        }
    }

    println!("Skin imported successfully to {:?}", out_dir);
    Ok(())
}

impl eframe::App for WarThunderCamoInstaller {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Load avatar image once
        if self.avatar_texture.is_none() {
            self.load_avatar_image(ctx);
        }

        // Updated menu bar
        egui::TopBottomPanel::top("menu_bar").show(ctx, |ui| {
            egui::menu::bar(ui, |ui| {
                ui.menu_button("File", |ui| {
                    if ui.button("Import Local Skin").clicked() {
                        self.show_import_popup = true;
                        ui.close_menu();
                    }
                    if ui.button("Clear Cache").clicked() {
                        if let Err(e) = self.clear_cache() {
                            self.error_message = Some(format!("Failed to clear cache: {}", e));
                        } else {
                            self.error_message = Some("Cache cleared successfully".to_string());
                        }
                        ui.close_menu();
                    }
                });
                ui.menu_button("About", |ui| {
                    if ui.button("About").clicked() {
                        self.show_about_popup = true;
                        ui.close_menu();
                    }
                });
            });
        });

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
                }
                Err(TryRecvError::Empty) => {
                    self.loading_images = false;
                    break;
                }
                Err(TryRecvError::Disconnected) => {
                    println!("Image receiver disconnected");
                    self.loading_images = false;
                    break;
                }
            }
        }

        match self.install_receiver.try_recv() {
            Ok(result) => match result {
                Ok(_) => self.error_message = Some("Skin installed successfully!".to_string()),
                Err(e) => self.error_message = Some(format!("Failed to install skin: {}", e)),
            },
            Err(TryRecvError::Empty) => {}
            Err(TryRecvError::Disconnected) => println!("Install receiver disconnected"),
        }

        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("War Thunder Camouflage Installer");
        
            ui.horizontal(|ui| {
                ui.label("Search:");
                let response = ui.text_edit_singleline(&mut self.search_query);
                if ui.button("Search").clicked()
                    || (response.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter)))
                {
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
                ui.label("Custom Structure:");
                if ui.text_edit_singleline(&mut self.custom_structure).changed() {}
                ui.label(
                    "Legend: %USERSKINS = Base directory, %NICKNAME = Creator's nickname, %SKIN_NAME = Skin name, %VEHICLE = Vehicle name",
                );
            });
        
            ui.checkbox(
                &mut self.use_custom_structure,
                "Use custom directory structure",
            );
        
            ui.horizontal(|ui| {
                if ui.button("Import Local Skin").clicked() {
                    self.show_import_popup = true;
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
                        self.install_skin(&zip_file_url);
                    }
                });
        
                self.is_initial_view = false;
            } else {
                ui.label("No camouflage selected");
            }
        });

// "About" popup window
if self.show_about_popup {
    egui::Window::new("About War Thunder Camouflage Installer")
        .open(&mut self.show_about_popup)
        .show(ctx, |ui| {
            ui.vertical_centered(|ui| {
                ui.heading("War Thunder Camouflage Installer");
                ui.label("Created by: hasnocool");
                ui.hyperlink_to("Visit my GitHub", "https://github.com/hasnocool");
                ui.label("Email: hasnocool@outlook.com");

                if let Some(avatar) = &self.avatar_texture {
                    let size = avatar.size_vec2() / 4.0; // Scale down the image
                    let radius = size.x.min(size.y) / 2.0; // Compute radius for circle clipping
                    let rect = ui.allocate_exact_size(size, egui::Sense::hover()).0;

                    // Draw circle filled with avatar image
                    let mut mesh = egui::Mesh::with_texture(avatar.id());
                    let n = 100; // Increased number of vertices for a smoother circle
                    for i in 0..=n {
                        let angle = i as f32 * std::f32::consts::TAU / n as f32;
                        let (sin, cos) = angle.sin_cos();
                        let offset = egui::Vec2::new(cos, sin) * radius;
                        let uv = (offset / radius + egui::Vec2::new(1.0, 1.0)) * 0.5;
                        
                        mesh.vertices.push(egui::epaint::Vertex {
                            pos: rect.center() + offset,
                            uv: egui::pos2(uv.x, uv.y),
                            color: egui::Color32::WHITE,
                        });
                    }

                    // Use triangle fan for more efficient rendering
                    for i in 1..n {
                        mesh.indices.push(0);
                        mesh.indices.push(i as u32);
                        mesh.indices.push((i + 1) as u32);
                    }

                    ui.painter().add(egui::Shape::mesh(mesh));
                }
            });
        });
}

        let mut close_popup = false;

        if self.show_import_popup {
            egui::Window::new("Import Local Skin")
                .open(&mut self.show_import_popup)
                .show(ctx, |ui| {
                    ui.label("Select directory for importing skins:");
                    if ui.button("Browse").clicked() {
                        if let Some(path) = FileDialog::new().pick_folder() {
                            self.selected_import_dir = Some(path);
                        }
                    }

                    if let Some(selected_dir) = &self.selected_import_dir {
                        ui.label(format!("Selected directory: {}", selected_dir.display()));
                    }

                    if ui.button("Import").clicked() {
                        if let Some(selected_import_dir) = &self.selected_import_dir {
                            let result = import_local_skin(
                                &self.wt_skins_dir.as_ref().unwrap_or(&PathBuf::from(".")),
                                selected_import_dir,
                            );
                            if let Err(e) = result {
                                self.error_message = Some(format!("Failed to import skin: {}", e));
                            } else {
                                self.error_message = Some("Local skin imported successfully!".to_string());
                            }
                        } else {
                            self.error_message = Some("No directory selected for import.".to_string());
                        }
                        close_popup = true;
                    }
                });
        }

        if close_popup {
            self.show_import_popup = false;
        }

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
            eprintln!("Failed to initialize the application: {:?}", e);
            eprintln!("Make sure the database file exists at: {:?}", db_path);
            Ok(())
        }
    }
}

