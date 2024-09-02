use thiserror::Error;

#[derive(Default, Debug, Clone)]
pub struct Camouflage {
    pub nickname: String,
    pub vehicle_name: String,
    pub description: String,
    pub file_size: String,
    pub post_date: String,
    pub hashtags: Vec<String>,
    pub tags: Vec<String>,  // New field for storing tags
    pub num_downloads: usize,
    pub num_likes: usize,
    pub zip_file_url: String,
    pub image_urls: Vec<String>,
}

#[derive(Error, Debug)]
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

// New implementation to convert InstallerError to rusqlite::Error
impl From<InstallerError> for rusqlite::Error {
    fn from(error: InstallerError) -> Self {
        match error {
            InstallerError::Sqlite(e) => e,
            _ => rusqlite::Error::SqliteFailure(
                rusqlite::ffi::Error::new(1), // Using a generic error code
                Some(error.to_string())
            ),
        }
    }
}

// Optional: If you want to use a wrapper enum for all error types
#[derive(Error, Debug)]
pub enum AppError {
    #[error("Installer error: {0}")]
    Installer(#[from] InstallerError),

    #[error("Database error: {0}")]
    Database(#[from] rusqlite::Error),
}