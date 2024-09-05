use eframe::egui;
use rusqlite::Connection;
use std::sync::{Arc, Mutex};
use std::sync::mpsc::Receiver;
use std::path::{Path, PathBuf};
use std::collections::{HashMap, VecDeque};

use crate::data::{Camouflage, InstallerError};
use crate::database;
use super::layout;
use super::handlers;

use crate::tags::TagCollection;
use serde_json;

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
}

impl WarThunderCamoInstaller {
    pub fn new(db_path: &Path) -> Result<Self, InstallerError> {
        let db_conn = Connection::open(db_path)?;
        let (_image_sender, image_receiver) = std::sync::mpsc::channel();
        let (_install_sender, install_receiver) = std::sync::mpsc::channel();

        database::initialize_database(&db_conn)?;

        let total_camos = database::update_total_camos(&db_conn)?;

        let images = Arc::new(Mutex::new(HashMap::new()));
        let loading_images = Arc::new(Mutex::new(false));
        let image_load_queue = Arc::new(Mutex::new(VecDeque::new()));

        let available_tags = database::fetch_tags(&db_conn, 0)?;

        let mut installer = Self {
            db_conn: Some(db_conn),
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

    pub fn new_without_db() -> Self {
        let (_image_sender, image_receiver) = std::sync::mpsc::channel();
        let (_install_sender, install_receiver) = std::sync::mpsc::channel();

        Self {
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
            wt_skins_dir: None,
            custom_structure: "%USERSKINS/%NICKNAME/%SKIN_NAME - %VEHICLE".to_string(),
            use_custom_structure: true,
            show_import_popup: false,
            show_about_popup: false,
            selected_import_dir: None,
            show_custom_structure_popup: false,
            image_load_queue: Arc::new(Mutex::new(VecDeque::new())),
            available_tags: Vec::new(),
            selected_tags: Vec::new(),
            custom_tags_input: String::new(),
            custom_tags: Vec::new(),
        }
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
        handlers::load_current_camo_images(self);
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
            Ok(Vec::new())
        }
    }

    pub fn export_tags(&self, path: &std::path::Path) -> Result<(), Box<dyn std::error::Error>> {
        let tags = TagCollection {
            available_tags: self.available_tags.clone(),
            custom_tags: self.custom_tags.clone(),
        };
        let json = serde_json::to_string_pretty(&tags)?;
        std::fs::write(path, json)?;
        Ok(())
    }

    pub fn import_tags(&mut self, path: &std::path::Path) -> Result<(), Box<dyn std::error::Error>> {
        let json = std::fs::read_to_string(path)?;
        let tags: TagCollection = serde_json::from_str(&json)?;
        self.available_tags = tags.available_tags;
        self.custom_tags = tags.custom_tags;
        Ok(())
    }
}

impl eframe::App for WarThunderCamoInstaller {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        handlers::update_image_grid(self, ctx);
        layout::build_ui(self, ctx);

        if *self.loading_images.lock().unwrap() {
            ctx.request_repaint();
        }
    }
}