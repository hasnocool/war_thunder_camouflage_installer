use eframe::egui;
use rusqlite::Connection;
use std::sync::{Arc, Mutex};
use std::sync::mpsc::Receiver;
use std::path::{Path, PathBuf};
use std::collections::{HashMap, VecDeque};

use crate::data::{Camouflage, InstallerError};
use crate::database;
use super::layout;
use crate::ui::handlers::image_handlers;
use crate::ui::handlers::utility_handlers;
use crate::ui::handlers::file_handlers;

use crate::tags::TagCollection;

type ImageReceiver = Arc<Mutex<Receiver<(String, Vec<u8>)>>>;

pub struct WarThunderCamoInstaller {
    pub db_conn: Option<Connection>,
    pub current_camo: Option<Camouflage>,
    pub _image_receiver: ImageReceiver,
    pub _install_receiver: Receiver<Result<(), String>>,
    pub images: Arc<Mutex<HashMap<String, egui::TextureHandle>>>,
    pub error_message: Option<String>,
    pub search_query: String,
    pub current_index: usize,
    pub total_camos: usize,
    pub search_results: Vec<Camouflage>,
    pub search_mode: bool,
    pub loading_images: Arc<Mutex<bool>>,
    pub image_load_queue: Arc<Mutex<VecDeque<String>>>,
    pub wt_skins_dir: Option<PathBuf>,
    pub custom_structure: String,
    pub use_custom_structure: bool,
    pub show_import_popup: bool,
    pub show_about_popup: bool,
    pub selected_import_dir: Option<PathBuf>,
    pub show_custom_structure_popup: bool,
    pub available_tags: Vec<String>,
    pub selected_tags: Vec<String>,
    pub custom_tags_input: String,
    pub custom_tags: Vec<String>,
    pub tag_filtering_enabled: bool,
    pub show_detailed_view: bool,
    pub current_page: usize,
    pub wt_dir_not_found: bool,  // New field
}

impl WarThunderCamoInstaller {
    pub fn new() -> Self {
        let (_image_sender, image_receiver) = std::sync::mpsc::channel();
        let (_install_sender, install_receiver) = std::sync::mpsc::channel();

        WarThunderCamoInstaller {
            db_conn: None,
            current_camo: None,
            _image_receiver: Arc::new(Mutex::new(image_receiver)),
            _install_receiver: install_receiver,
            images: Arc::new(Mutex::new(HashMap::new())),
            error_message: Some("No database loaded. Some features may be limited.".to_string()),
            search_query: String::new(),
            current_index: 0,
            total_camos: 0,
            search_results: Vec::new(),
            search_mode: false,
            loading_images: Arc::new(Mutex::new(false)),
            image_load_queue: Arc::new(Mutex::new(VecDeque::new())),
            wt_skins_dir: None,
            custom_structure: "%USERSKINS/%NICKNAME/%SKIN_NAME - %VEHICLE".to_string(),
            use_custom_structure: true,
            show_import_popup: false,
            show_about_popup: false,
            selected_import_dir: None,
            show_custom_structure_popup: false,
            available_tags: Vec::new(),
            selected_tags: Vec::new(),
            custom_tags_input: String::new(),
            custom_tags: Vec::new(),
            tag_filtering_enabled: true,
            show_detailed_view: false,
            current_page: 0,
            wt_dir_not_found: true,  // Initialize to true
        }
    }

    // In src/ui/app.rs, remove the unused variable:
    pub fn start_skin_installation(&mut self, zip_url: &str) {
        if self.current_camo.is_some() {
            file_handlers::install_skin(self, zip_url);
            self.error_message = Some("Skin installation initiated.".to_string());
        } else {
            self.error_message = Some("No camouflage selected for installation.".to_string());
        }
    }

    pub fn set_wt_skins_directory(&mut self, path: &Path) {
        self.wt_skins_dir = Some(path.to_path_buf());
        self.wt_dir_not_found = false;
    }

    pub fn initialize_database(&mut self, db_path: &Path) -> Result<(), InstallerError> {
        let db_conn = Connection::open(db_path)?;
        database::initialize_database(&db_conn)?;
    
        self.db_conn = Some(db_conn);
    
        // Fetch all camouflages on initial load and update total camouflages
        let all_camouflages = self.fetch_camouflages(None, &[])?;
        self.search_results = all_camouflages.clone();
        self.total_camos = all_camouflages.len();
    
        if let Some(first_camo) = all_camouflages.first() {
            self.set_current_camo(0, first_camo.clone());
        }
    
        Ok(())
    }
    

    pub fn fetch_camouflage_by_index(&self, index: usize) -> Result<Option<(usize, Camouflage)>, InstallerError> {
        if let Some(db_conn) = &self.db_conn {
            database::fetch_camouflage_by_index(db_conn, index)
        } else {
            Ok(None)
        }
    }

    pub fn set_current_camo(&mut self, index: usize, camo: Camouflage) {
        self.current_index = index;
        self.current_camo = Some(camo);

        self.clear_images();
        image_handlers::load_current_camo_images(self);
    }

    pub fn clear_images(&self) {
        let mut images = self.images.lock().unwrap();
        images.clear();

        let mut queue = self.image_load_queue.lock().unwrap();
        queue.clear();
    }

    pub fn fetch_camouflages(&self, query: Option<&str>, selected_tags: &[String]) -> Result<Vec<Camouflage>, InstallerError> {
        if let Some(db_conn) = &self.db_conn {
            database::fetch_camouflages(db_conn, query, selected_tags)
        } else {
            Ok(Vec::new()) // Return empty list if no database is loaded
        }
    }

    pub fn export_tags(&self, path: &Path) -> Result<(), Box<dyn std::error::Error>> {
        let tags = TagCollection {
            available_tags: self.available_tags.clone(),
            custom_tags: self.custom_tags.clone(),
        };
        let json = serde_json::to_string_pretty(&tags)?;
        std::fs::write(path, json)?;
        Ok(())
    }

    pub fn import_tags(&mut self, path: &Path) -> Result<(), Box<dyn std::error::Error>> {
        let json = std::fs::read_to_string(path)?;
        let tags: TagCollection = serde_json::from_str(&json)?;
        self.available_tags = tags.available_tags;
        self.custom_tags = tags.custom_tags;
        Ok(())
    }

    pub fn update(&mut self, ctx: &egui::Context) {
        utility_handlers::update_app_state(self);
        image_handlers::update_image_grid(self, ctx);
        if self.use_custom_structure {
            file_handlers::apply_custom_structure(self);
        }

        if self.wt_dir_not_found {
            self.show_wt_dir_not_found_popup(ctx);
        }
    }

    fn show_wt_dir_not_found_popup(&mut self, ctx: &egui::Context) {
        egui::Window::new("War Thunder Directory Not Found")
            .collapsible(false)
            .resizable(false)
            .show(ctx, |ui| {
                ui.label("The War Thunder directory could not be found automatically.");
                ui.label("Please select the War Thunder UserSkins directory manually.");
                if ui.button("Select Directory").clicked() {
                    if let Some(path) = rfd::FileDialog::new().pick_folder() {
                        self.set_wt_skins_directory(&path);
                    }
                }
            });
    }
}

impl eframe::App for WarThunderCamoInstaller {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.update(ctx);
        layout::build_ui(self, ctx);

        if *self.loading_images.lock().unwrap() {
            ctx.request_repaint();
        }
    }
}


