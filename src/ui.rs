use eframe::egui;
use std::sync::{Arc, Mutex};
use std::sync::mpsc::{Receiver, Sender};
use std::path::{Path, PathBuf};
use std::collections::{HashMap, VecDeque};
use image::GenericImageView;
use crate::{
    data::{Camouflage, InstallerError},
    database,
    image_utils,
    file_operations,
    path_utils,
};

pub struct WarThunderCamoInstaller {
    db_conn: rusqlite::Connection,
    current_camo: Option<Camouflage>,
    _image_receiver: Receiver<(String, Vec<u8>)>,
    image_sender: Sender<(String, Vec<u8>)>,
    _install_receiver: Receiver<Result<(), String>>,
    images: Arc<Mutex<HashMap<String, egui::TextureHandle>>>,
    error_message: Option<String>,
    search_query: String,
    current_index: usize,
    total_camos: usize,
    loading_images: Arc<Mutex<bool>>,
    image_load_queue: Arc<Mutex<VecDeque<String>>>,
    wt_skins_dir: Option<PathBuf>,
    custom_structure: String,
    use_custom_structure: bool,
    show_import_popup: bool,
    show_about_popup: bool,
    cache_dir: PathBuf,
    selected_import_dir: Option<PathBuf>,
    avatar_texture: Option<egui::TextureHandle>,
    show_custom_structure_popup: bool,
}

impl WarThunderCamoInstaller {
    pub fn new(db_path: &Path) -> Result<Self, InstallerError> {
        let db_conn = rusqlite::Connection::open(db_path)?;
        let (image_sender, image_receiver) = std::sync::mpsc::channel();
        let (_install_sender, install_receiver) = std::sync::mpsc::channel();

        let total_camos = database::update_total_camos(&db_conn)?;

        let images = Arc::new(Mutex::new(HashMap::new()));
        let loading_images = Arc::new(Mutex::new(false));
        let image_load_queue = Arc::new(Mutex::new(VecDeque::new()));

        let mut installer = Self {
            db_conn,
            current_camo: None,
            _image_receiver: image_receiver,
            image_sender,
            _install_receiver: install_receiver,
            images,
            error_message: None,
            search_query: String::new(),
            current_index: 0,
            total_camos,
            loading_images,
            wt_skins_dir: None,
            custom_structure: "%USERSKINS/%NICKNAME/%SKIN_NAME - %VEHICLE".to_string(),
            use_custom_structure: true,
            show_import_popup: false,
            show_about_popup: false,
            cache_dir: PathBuf::from("cache"),
            selected_import_dir: None,
            avatar_texture: None,
            show_custom_structure_popup: false,
            image_load_queue,
        };

        // Load the first camouflage on startup
        if let Ok(Some((index, camo))) = installer.fetch_camouflage("") {
            installer.set_current_camo(index, camo);
        } else {
            installer.error_message = Some("Failed to load the initial camouflage.".to_string());
        }

        Ok(installer)
    }

    fn show_about_popup(&mut self, ctx: &egui::Context) {
        if !self.show_about_popup {
            return;
        }

        let mut should_close = false;
        egui::Window::new("About War Thunder Camouflage Installer")
            .collapsible(false)
            .resizable(false)
            .show(ctx, |ui| {
                ui.vertical_centered(|ui| {
                    ui.heading("War Thunder Camouflage Installer");
                    ui.label("Created by: hasnocool");
                    ui.hyperlink_to("Visit my GitHub", "https://github.com/hasnocool");
                    ui.label("Email: hasnocool@outlook.com");
                    if let Some(avatar) = &self.avatar_texture {
                        let size = avatar.size_vec2() / 4.0;
                        let radius = size.x.min(size.y) / 2.0;
                        let rect = ui.allocate_exact_size(size, egui::Sense::hover()).0;
                        let mut mesh = egui::Mesh::with_texture(avatar.id());
                        let n = 100;
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
                        for i in 1..n {
                            mesh.indices.push(0);
                            mesh.indices.push(i as u32);
                            mesh.indices.push((i + 1) as u32);
                        }
                        ui.painter().add(egui::Shape::mesh(mesh));
                    }
                    ui.add_space(10.0);
                    if ui.button("Close").clicked() {
                        should_close = true;
                    }
                });
            });

        if should_close {
            self.show_about_popup = false;
        }
    }

    fn perform_search(&mut self) {
        match self.fetch_camouflage(&self.search_query) {
            Ok(Some((index, camo))) => {
                self.set_current_camo(index, camo);
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

    fn fetch_camouflage(&self, query: &str) -> Result<Option<(usize, Camouflage)>, InstallerError> {
        database::fetch_camouflage(&self.db_conn, query)
    }

    fn set_current_camo(&mut self, index: usize, camo: Camouflage) {
        self.current_index = index;
        self.current_camo = Some(camo);
        self.load_current_camo_images();
    }

    fn show_image_grid(&self, ui: &mut egui::Ui) {
        let images = self.images.lock().unwrap();
        if images.is_empty() {
            ui.label("No images to display.");
            return;
        }

        // Get the avatar image URL to skip in the grid
        let avatar_url = self.current_camo.as_ref().map(|camo| &camo.image_urls[0]);

        let available_width = ui.available_width();
        let image_width = 150.0; // Desired width for each image in the grid
        let num_columns = (available_width / image_width).floor() as usize;
        let mut columns_filled = 0;

        egui::Grid::new("image_grid")
            .num_columns(num_columns)
            .spacing([10.0, 10.0])
            .striped(true)
            .show(ui, |ui| {
                for (url, texture_handle) in images.iter() {
                    // Skip the avatar image
                    if Some(url) == avatar_url {
                        continue;
                    }

                    let size = texture_handle.size_vec2();
                    let (width, height) = (size.x, size.y);

                    // Adjust image size to fit within the grid cell while maintaining aspect ratio
                    let aspect_ratio = width / height;
                    let scaled_width = image_width;
                    let scaled_height = scaled_width / aspect_ratio;

                    ui.add(egui::Image::new(texture_handle.id(), [scaled_width, scaled_height]));

                    columns_filled += 1;
                    if columns_filled >= num_columns {
                        ui.end_row();
                        columns_filled = 0;
                    }
                }
            });
    }

    fn load_current_camo_images(&self) {
        if let Some(camo) = &self.current_camo {
            let mut queue = self.image_load_queue.lock().unwrap();
            for url in &camo.image_urls {
                if !self.images.lock().unwrap().contains_key(url) {
                    queue.push_back(url.clone());
                }
            }
        }
    }

    fn update_image_grid(&self, ctx: &egui::Context) {
        let mut loading = self.loading_images.lock().unwrap();
        if *loading {
            return;
        }

        let mut queue = self.image_load_queue.lock().unwrap();
        if let Some(url) = queue.pop_front() {
            *loading = true;
            let sender_clone = self.image_sender.clone();
            let cache_dir_clone = self.cache_dir.clone();
            let images = self.images.clone();
            let loading_images = self.loading_images.clone();
            let ctx = ctx.clone();

            std::thread::spawn(move || {
                if let Ok(()) = image_utils::load_image(sender_clone.clone(), url.clone(), cache_dir_clone.clone()) {
                    if let Ok(image_data) = std::fs::read(cache_dir_clone.join(url.split('/').last().unwrap())) {
                        if let Ok(dynamic_image) = image::load_from_memory(&image_data) {
                            let (width, height) = dynamic_image.dimensions();
                            let rgba_image = dynamic_image.to_rgba8();
                            let image = egui::ColorImage::from_rgba_unmultiplied(
                                [width as usize, height as usize],
                                rgba_image.as_raw(),
                            );
                            ctx.request_repaint();
                            let texture = ctx.load_texture(
                                url.clone(),
                                image,
                                egui::TextureOptions::default(),
                            );
                            images.lock().unwrap().insert(url, texture);
                        }
                    }
                }
                *loading_images.lock().unwrap() = false;
            });
        }
    }

    fn show_custom_structure_popup(&mut self, ctx: &egui::Context) {
        if self.show_custom_structure_popup {
            egui::Window::new("Custom Structure Settings")
                .collapsible(false)
                .resizable(false)
                .min_width(400.0)
                .show(ctx, |ui| {
                    ui.vertical(|ui| {
                        ui.horizontal(|ui| {
                            ui.label("Custom Structure:");
                            ui.add(egui::TextEdit::singleline(&mut self.custom_structure)
                                .hint_text("%USERSKINS/%NICKNAME/%SKIN_NAME - %VEHICLE")
                                .desired_width(350.0));
                        });
                        ui.horizontal(|ui| {
                            ui.label("Use custom directory structure:");
                            ui.checkbox(&mut self.use_custom_structure, "");
                        });

                        ui.add_space(10.0);

                        if ui.button("Close").clicked() {
                            self.show_custom_structure_popup = false;
                        }
                    });
                });
        }
    }

    fn install_skin(&mut self, zip_url: &str) -> Result<(), InstallerError> {
        if let Some(skins_directory) = &self.wt_skins_dir {
            let custom_structure = if self.use_custom_structure {
                Some(self.custom_structure.as_str())
            } else {
                None
            };

            let out_dir = if let Some(custom) = custom_structure {
                path_utils::generate_custom_path(skins_directory.as_path(), custom, self.current_camo.as_ref().unwrap())
            } else {
                skins_directory.join(&self.current_camo.as_ref().unwrap().vehicle_name)
            };

            // Download and extract the skin
            // This is a placeholder. You should implement the actual download and extraction logic.
            println!("Downloading skin from {} to {:?}", zip_url, out_dir);

            self.error_message = Some("Skin installed successfully".to_string());
            Ok(())
        } else {
            Err(InstallerError::Custom("War Thunder skins directory not selected".to_string()))
        }
    }

    fn show_next_camo(&mut self) {
        if self.current_index < self.total_camos - 1 {
            if let Ok(Some((index, camo))) = self.fetch_camouflage(&(self.current_index + 1).to_string()) {
                self.set_current_camo(index, camo);
            } else {
                self.error_message = Some("Failed to load the next camouflage.".to_string());
            }
        }
    }

    fn show_previous_camo(&mut self) {
        if self.current_index > 0 {
            if let Ok(Some((index, camo))) = self.fetch_camouflage(&(self.current_index - 1).to_string()) {
                self.set_current_camo(index, camo);
            } else {
                self.error_message = Some("Failed to load the previous camouflage.".to_string());
            }
        }
    }
}

impl eframe::App for WarThunderCamoInstaller {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.update_image_grid(ctx);

        // Top Panel for Menu
        egui::TopBottomPanel::top("menu_bar").show(ctx, |ui| {
            egui::menu::bar(ui, |ui| {
                ui.menu_button("File", |ui| {
                    if ui.button("Set War Thunder Skins Directory").clicked() {
                        if let Some(path) = rfd::FileDialog::new().pick_folder() {
                            self.wt_skins_dir = Some(path);
                        }
                        ui.close_menu();
                    }
                    if ui.button("Custom Structure Settings").clicked() {
                        self.show_custom_structure_popup = true;
                        ui.close_menu();
                    }
                    if ui.button("Import Local Skin").clicked() {
                        self.show_import_popup = true;
                        ui.close_menu();
                    }
                    if ui.button("Clear Cache").clicked() {
                        if let Err(e) = image_utils::clear_cache(&self.cache_dir) {
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

        // Header Panel for Search Bar
        egui::TopBottomPanel::top("header_panel")
            .min_height(50.0)
            .show(ctx, |ui| {
                ui.horizontal_centered(|ui| {
                    ui.heading("Search for Camouflages");

                    let (rect, _response) = ui.allocate_exact_size(egui::vec2(ui.available_width() * 0.7, 40.0), egui::Sense::click_and_drag());

                    // Draw search bar with rounded rectangle background
                    let rect_shape = egui::epaint::RectShape {
                        rect,
                        rounding: egui::Rounding::same(5.0),
                        fill: egui::Color32::from_gray(240),
                        stroke: egui::Stroke::new(1.0, egui::Color32::from_gray(200)),
                    };

                    ui.painter().add(egui::Shape::Rect(rect_shape));

                    let search_bar = ui.put(rect.shrink(8.0), 
                        egui::TextEdit::singleline(&mut self.search_query)
                            .hint_text("Search for camouflages...")
                            .desired_width(rect.width() - 40.0)
                    );

                    let button_rect = egui::Rect::from_min_size(
                        egui::pos2(rect.right() - 32.0, rect.top() + 4.0),
                        egui::vec2(28.0, 32.0),
                    );

                    if ui.put(button_rect, egui::Button::new("🔍")).clicked() 
                        || (search_bar.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter))) 
                    {
                        self.perform_search();
                    }
                });
            });

        // Central Panel for Main Content
        egui::CentralPanel::default().show(ctx, |ui| {
            egui::ScrollArea::vertical().show(ui, |ui| {
                ui.vertical_centered(|ui| {
                    ui.add_space(10.0);

                    if let Some(camo) = &self.current_camo {
                        let camo_clone = camo.clone();
                        ui.heading(&camo_clone.vehicle_name);
                        ui.label(&camo_clone.description);

                        // Display the avatar (first image)
                        if let Some(avatar_texture) = self.images.lock().unwrap().get(&camo_clone.image_urls[0]) {
                            let size = avatar_texture.size_vec2();
                            ui.image(avatar_texture.id(), size);
                        }

                        ui.label(format!("Nickname: {}", camo_clone.nickname));
                        ui.label(format!("File size: {}", camo_clone.file_size));
                        ui.label(format!("Posted on: {}", camo_clone.post_date));
                        ui.label(format!("Hashtags: {}", camo_clone.hashtags.join(", ")));
                        ui.label(format!("Downloads: {}", camo_clone.num_downloads));
                        ui.label(format!("Likes: {}", camo_clone.num_likes));

                        ui.separator();  // Add a separator before showing the images grid
                        self.show_image_grid(ui);  // Show images as a responsive grid

                    } else {
                        ui.label("No camouflage selected");
                    }
                });
            });
        });

        // Footer Panel for Buttons
        egui::TopBottomPanel::bottom("footer_panel")
            .min_height(50.0)
            .show(ctx, |ui| {
                ui.horizontal_centered(|ui| {
                    if let Some(camo) = &self.current_camo {
                        let zip_file_url = camo.zip_file_url.clone(); // Clone the URL outside the mutable borrow

                        if ui.button("Install").clicked() {
                            if let Err(e) = self.install_skin(&zip_file_url) {
                                self.error_message = Some(format!("Failed to install skin: {:?}", e));
                            } else {
                                self.error_message = Some("Skin installed successfully".to_string());
                            }
                        }

                        if ui.button("Previous").clicked() {
                            self.show_previous_camo();
                        }

                        ui.label(format!("{}/{}", self.current_index + 1, self.total_camos));

                        if ui.button("Next").clicked() {
                            self.show_next_camo();
                        }
                    }
                });
            });

        // Additional Popups
        self.show_custom_structure_popup(ctx);
        self.show_about_popup(ctx);

        if self.show_import_popup {
            let mut show_import_popup = self.show_import_popup;
            egui::Window::new("Import Local Skin")
                .open(&mut show_import_popup)
                .show(ctx, |ui| {
                    ui.label("Select directory for importing skins:");
                    if ui.button("Browse").clicked() {
                        if let Some(path) = rfd::FileDialog::new().pick_folder() {
                            self.selected_import_dir = Some(path);
                        }
                    }

                    if let Some(selected_dir) = &self.selected_import_dir {
                        ui.label(format!("Selected directory: {}", selected_dir.display()));
                    }

                    if ui.button("Import").clicked() {
                        if let Some(selected_import_dir) = &self.selected_import_dir {
                            let result = file_operations::import_local_skin(
                                self.wt_skins_dir.as_ref().unwrap_or(&PathBuf::from(".")),
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
                        self.show_import_popup = false;
                    }
                });
            self.show_import_popup = show_import_popup;
        }

        if *self.loading_images.lock().unwrap() {
            ctx.request_repaint();
        }
    }
}
