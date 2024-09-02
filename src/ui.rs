use eframe::egui;
use std::sync::{Arc, Mutex};
use std::sync::mpsc::{Receiver};  
use std::path::{Path, PathBuf};
use std::collections::{HashMap, VecDeque};
use image::GenericImageView;
use rayon::prelude::*;
use std::sync::mpsc;
use crate::{
    data::{Camouflage, InstallerError},
    database,
    image_utils,
    file_operations,
    path_utils,
};

type ImageReceiver = Arc<Mutex<Receiver<(String, Vec<u8>)>>>;

pub struct WarThunderCamoInstaller {
    db_conn: rusqlite::Connection,
    current_camo: Option<Camouflage>,
    _image_receiver: ImageReceiver, 
    _install_receiver: Receiver<Result<(), String>>,
    images: Arc<Mutex<HashMap<String, egui::TextureHandle>>>,
    error_message: Option<String>,
    search_query: String,
    current_index: usize,
    total_camos: usize,
    search_results: Vec<Camouflage>, 
    search_mode: bool, 
    loading_images: Arc<Mutex<bool>>,
    image_load_queue: Arc<Mutex<VecDeque<String>>>,
    wt_skins_dir: Option<PathBuf>,
    custom_structure: String,
    use_custom_structure: bool,
    show_import_popup: bool,
    show_about_popup: bool,
    selected_import_dir: Option<PathBuf>,
    #[allow(dead_code)]
    avatar_texture: Option<egui::TextureHandle>,
    show_custom_structure_popup: bool,
    available_tags: Vec<String>, 
    selected_tags: Vec<String>,
    custom_tags_input: String,
    custom_tags: Vec<String>,
}

impl WarThunderCamoInstaller {
    pub fn new(db_path: &Path) -> Result<Self, InstallerError> {
        let db_conn = rusqlite::Connection::open(db_path)?;
        let (_image_sender, image_receiver) = std::sync::mpsc::channel();  
        let (_install_sender, install_receiver) = std::sync::mpsc::channel();

        database::initialize_database(&db_conn)?;

        let total_camos = database::update_total_camos(&db_conn)?;

        let images = Arc::new(Mutex::new(HashMap::new()));
        let loading_images = Arc::new(Mutex::new(false));
        let image_load_queue = Arc::new(Mutex::new(VecDeque::new()));

        // Corrected function call for fetching tags
        let available_tags = database::fetch_tags(&db_conn, 0)?; // Replace with actual logic to fetch all tags

        let mut installer = Self {
            db_conn,
            current_camo: None,
            _image_receiver: Arc::new(Mutex::new(image_receiver)), 
            _install_receiver: install_receiver,
            images,
            error_message: None,
            search_query: String::new(),
            current_index: 0,
            total_camos,
            search_results: Vec::new(),
            search_mode: false,
            loading_images,
            wt_skins_dir: None,
            custom_structure: "%USERSKINS/%NICKNAME/%SKIN_NAME - %VEHICLE".to_string(),
            use_custom_structure: true,
            show_import_popup: false,
            show_about_popup: false,
            selected_import_dir: None,
            avatar_texture: None,
            show_custom_structure_popup: false,
            image_load_queue,
            available_tags, 
            selected_tags: Vec::new(), 
            custom_tags_input: String::new(),
            custom_tags: Vec::new(),
        };

        if let Ok(Some((index, camo))) = installer.fetch_camouflage_by_index(0) {
            installer.set_current_camo(index, camo);
        } else {
            installer.error_message = Some("Failed to load the initial camouflage.".to_string());
        }

        Ok(installer)
    }

    fn add_custom_tags(&mut self) {
        let new_tags: Vec<String> = self.custom_tags_input
            .split(',')
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .collect();
        self.custom_tags.extend(new_tags);
        self.custom_tags.sort();
        self.custom_tags.dedup();
        self.custom_tags_input.clear();
    }

    fn perform_search(&mut self) {
        let query = if self.search_query.is_empty() { None } else { Some(self.search_query.as_str()) };
        match self.fetch_camouflages(query, &self.selected_tags) {
            Ok(results) => {
                self.search_results = results;
                self.search_mode = true;
                if !self.search_results.is_empty() {
                    self.current_index = 0;
                    self.set_current_camo(0, self.search_results[0].clone());
                } else {
                    self.current_index = 0;
                    self.current_camo = None;
                    self.clear_images();
                    self.error_message = Some("No results found".to_string());
                }
            }
            Err(e) => {
                self.error_message = Some(format!("Search error: {:?}", e));
                self.search_results.clear();
                self.current_camo = None;
                self.clear_images();
            }
        }
    }

    fn fetch_camouflages(&self, query: Option<&str>, selected_tags: &[String]) -> Result<Vec<Camouflage>, InstallerError> {
        if !selected_tags.is_empty() || query.is_some() {
            database::fetch_camouflages(&self.db_conn, query, selected_tags)
        } else {
            database::fetch_all_camouflages(&self.db_conn)
        }
    }    


    fn fetch_camouflage_by_index(&self, index: usize) -> Result<Option<(usize, Camouflage)>, InstallerError> {
        database::fetch_camouflage_by_index(&self.db_conn, index)
    }

    #[allow(dead_code)]
    fn filter_camouflages_by_tags(&self, selected_tags: &[String], query: Option<&str>) -> Result<Vec<Camouflage>, InstallerError> {
        let mut sql_query = String::from(
            "SELECT DISTINCT c.rowid, c.vehicle_name, c.description, c.image_urls, c.zip_file_url, c.hashtags, c.file_size, c.num_downloads, c.num_likes, c.post_date, c.nickname
            FROM camouflages c
            JOIN camouflage_tags ct ON c.rowid = ct.camouflage_id
            JOIN tags t ON ct.tag_id = t.id
            WHERE "
        );
    
        // Add tag conditions
        let tag_conditions: Vec<String> = selected_tags.iter().map(|_| "t.name = ?".to_string()).collect();
        sql_query.push_str(&tag_conditions.join(" OR "));
    
        // Add search query condition if provided
        if query.is_some() {
            sql_query.push_str(" AND (c.vehicle_name LIKE ? OR c.description LIKE ?)");
        }
    
        let mut stmt = self.db_conn.prepare(&sql_query).map_err(InstallerError::from)?;
    
    // Prepare parameters
    let mut params: Vec<&dyn rusqlite::ToSql> = selected_tags.iter().map(|s| s as &dyn rusqlite::ToSql).collect();
    let like_pattern: String;
    if let Some(q) = query {
        like_pattern = format!("%{}%", q);
        params.push(&like_pattern);
        params.push(&like_pattern);
    }

        let camo_iter = stmt.query_map(params.as_slice(), |row| {
            let camo_id: usize = row.get(0)?;
            let tags = database::fetch_tags(&self.db_conn, camo_id)
                .map_err(InstallerError::from)?;
    
            Ok(Camouflage {
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
                tags,
                file_size: row.get(6)?,
                num_downloads: row.get(7)?,
                num_likes: row.get(8)?,
                post_date: row.get(9)?,
                nickname: row.get(10)?,
            })
        }).map_err(InstallerError::from)?;
    
        camo_iter.collect::<Result<Vec<_>, rusqlite::Error>>().map_err(InstallerError::from)
    }
    
    
    

    fn set_current_camo(&mut self, index: usize, camo: Camouflage) {
        self.current_index = index;
        self.current_camo = Some(camo);
        
        self.clear_images();
        self.load_current_camo_images();
    }

    fn clear_images(&self) {
        let mut images = self.images.lock().unwrap();
        images.clear();

        let mut queue = self.image_load_queue.lock().unwrap();
        queue.clear();
    }

    fn show_image_grid(&self, ui: &mut egui::Ui) {
        let images = self.images.lock().unwrap();
        if images.is_empty() {
            ui.label("No images to display.");
            return;
        }

        let avatar_url = self.current_camo.as_ref().map(|camo| &camo.image_urls[0]);

        let available_width = ui.available_width();
        let image_width = 150.0;
        let num_columns = (available_width / image_width).floor() as usize;
        let mut columns_filled = 0;

        egui::Grid::new("image_grid")
            .num_columns(num_columns)
            .spacing([10.0, 10.0])
            .striped(true)
            .show(ui, |ui| {
                for (url, texture_handle) in images.iter() {
                    if Some(url) == avatar_url {
                        continue;
                    }

                    let size = texture_handle.size_vec2();
                    let (width, height) = (size.x, size.y);

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
        if queue.is_empty() {
            return;
        }

        *loading = true;
        let urls: Vec<String> = queue.drain(..).collect();
        let images = self.images.clone();
        let ctx = ctx.clone();
        let loading_images = self.loading_images.clone();

        std::thread::spawn(move || {
            let (tx, rx) = mpsc::channel();
            let tx = Arc::new(Mutex::new(tx));

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


    #[allow(dead_code)]
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

            println!("Downloading skin from {} to {:?}", zip_url, out_dir);

            self.error_message = Some("Skin installed successfully".to_string());
            Ok(())
        } else {
            Err(InstallerError::Custom("War Thunder skins directory not selected".to_string()))
        }
    }

    fn show_next_camo(&mut self) {
        if self.search_mode {
            if self.current_index < self.search_results.len() - 1 {
                self.current_index += 1;
                if let Some(camo) = self.search_results.get(self.current_index) {
                    self.set_current_camo(self.current_index, camo.clone());
                }
            }
        } else if self.current_index < self.total_camos - 1 {
            let next_index = self.current_index + 1;
            if let Ok(Some((index, camo))) = self.fetch_camouflage_by_index(next_index) {
                self.set_current_camo(index, camo);
            } else {
                self.error_message = Some("Failed to load the next camouflage.".to_string());
            }
        }
    }

    fn show_previous_camo(&mut self) {
        if self.search_mode {
            if self.current_index > 0 {
                self.current_index -= 1;
                if let Some(camo) = self.search_results.get(self.current_index) {
                    self.set_current_camo(self.current_index, camo.clone());
                }
            }
        } else if self.current_index > 0 {
            let prev_index = self.current_index - 1;
            if let Ok(Some((index, camo))) = self.fetch_camouflage_by_index(prev_index) {
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
                        if let Err(e) = image_utils::clear_cache() {
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

        // Header Panel for Search Bar and Tag Filters
        egui::TopBottomPanel::top("header_panel").min_height(70.0).show(ctx, |ui| {
            ui.vertical_centered_justified(|ui| {
                let top_padding = 20.0;
                let bottom_padding = 10.0;

                ui.add_space(top_padding);

                ui.horizontal(|ui| {
                    let side_padding = 20.0;
                    let total_width = ui.available_width() - (2.0 * side_padding);

                    ui.add_space(side_padding);

                    let button_width = 40.0;
                    let search_bar_width = total_width - button_width - 10.0;

                    let search_bar = ui.add_sized(
                        [search_bar_width, 30.0],
                        egui::TextEdit::singleline(&mut self.search_query)
                            .hint_text("Search for camouflages...")
                    );

                    ui.add_space(10.0);

                    if ui.add_sized([button_width, 30.0], egui::Button::new("🔍")).clicked()
                        || (search_bar.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter)))
                    {
                        self.perform_search();
                    }

                    ui.add_space(side_padding);
                });

                ui.add_space(10.0);

                ui.horizontal(|ui| {
                    ui.label("Filter by tags:");
            
                    let all_tags = self.available_tags.iter().chain(self.custom_tags.iter());
                    for tag in all_tags {
                        let mut is_selected = self.selected_tags.contains(tag);
                        if ui.checkbox(&mut is_selected, tag).clicked() {
                            if is_selected {
                                self.selected_tags.push(tag.clone());
                            } else {
                                self.selected_tags.retain(|t| t != tag);
                            }
                        }
                    }
            
                    if ui.button("Apply Filter").clicked() {
                        self.perform_search();
                    }
                });

                ui.add_space(bottom_padding);
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

                        if let Some(avatar_texture) = self.images.lock().unwrap().get(&camo_clone.image_urls[0]) {
                            let size = avatar_texture.size_vec2();
                            ui.image(avatar_texture.id(), size);
                        }

                        ui.label(format!("Nickname: {}", camo_clone.nickname));
                        ui.label(format!("File size: {}", camo_clone.file_size));
                        ui.label(format!("Posted on: {}", camo_clone.post_date));
                        ui.label(format!("Hashtags: {}", camo_clone.hashtags.join(", ")));
                        ui.label(format!("Tags: {}", camo_clone.tags.join(", "))); 
                        ui.label(format!("Downloads: {}", camo_clone.num_downloads));
                        ui.label(format!("Likes: {}", camo_clone.num_likes));

                        ui.separator();
                        self.show_image_grid(ui);

                    } else {
                        ui.label("No camouflage selected");
                        if let Some(error) = &self.error_message {
                            ui.label(error);
                        }
                    }
                });
            });
        });
        
// Footer Panel for Buttons and Custom Tags Input
egui::TopBottomPanel::bottom("footer_panel")
    .min_height(100.0)
    .show(ctx, |ui| {
        ui.add_space(10.0);

        ui.horizontal(|ui| {
            ui.add_space(10.0);

            if !self.search_results.is_empty() {
                if ui.button("Previous").clicked() {
                    self.show_previous_camo();
                }

                ui.label(format!("{}/{}", self.current_index + 1, self.search_results.len()));

                if ui.button("Next").clicked() {
                    self.show_next_camo();
                }

                ui.add_space(20.0); // Add some space between navigation and install button
            } else {
                ui.label("No results");
            }

            if let Some(camo) = &self.current_camo {
                let zip_file_url = camo.zip_file_url.clone();

                if ui.button("Install").clicked() {
                    match self.install_skin(&zip_file_url) {
                        Ok(_) => {
                            self.error_message = Some("Skin installed successfully".to_string());
                        }
                        Err(e) => {
                            self.error_message = Some(format!("Failed to install skin: {:?}", e));
                        }
                    }
                }
            }

            // Push the custom tags input to the right
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                if ui.button("Add Tags").clicked() {
                    self.add_custom_tags();
                }

                let input = ui.add_sized(
                    [200.0, 30.0], // Adjust width as needed
                    egui::TextEdit::singleline(&mut self.custom_tags_input)
                        .hint_text("Enter tags separated by commas")
                );

                if input.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter)) {
                    self.add_custom_tags();
                }

                ui.label("Custom Tags:");

                ui.add_space(10.0);
            });
        });

        ui.add_space(10.0);
    });

        // Additional Popups
        self.show_custom_structure_popup(ctx);

        // Corrected field usage instead of method call
        if self.show_about_popup {
            egui::Window::new("About").show(ctx, |ui| {
                ui.label("War Thunder Camouflage Installer v1.0.3-beta");
                ui.label("Developed by XYZ.");
                if ui.button("Close").clicked() {
                    self.show_about_popup = false;
                }
            });
        }

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



