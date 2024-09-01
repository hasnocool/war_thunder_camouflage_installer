
#[derive(Default, Debug, Clone)]
pub struct Camouflage {
    pub nickname: String,
    pub vehicle_name: String,
    pub description: String,
    pub file_size: String,
    pub post_date: String,
    pub hashtags: Vec<String>,
    pub num_downloads: usize,
    pub num_likes: usize,
    pub zip_file_url: String,
    pub image_urls: Vec<String>,
}

#[derive(thiserror::Error, Debug)]
pub enum InstallerError {
    #[error("SQLite error: {0}")]
    Sqlite(#[from] rusqlite::Error),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Custom error: {0}")]
    Custom(String),
}

impl From<String> for InstallerError {
    fn from(err: String) -> Self {
        InstallerError::Custom(err)
    }
}