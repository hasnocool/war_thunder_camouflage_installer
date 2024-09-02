![War Thunder Camouflage Installer Logo](https://github.com/hasnocool/war_thunder_camouflage_installer/blob/master/assets/logo.png?raw=true)

> **Note:** You may need `git-lfs` installed in order to download the database with git, otherwise you will have to manually download it and ensure it is in the same directory as the executable.
> **Note:** Images may take a second to appear as they are being pulled from WT-LIVE. The code will be updated to alleviate this ASAP.

**Database Last Updated:** 08/29/2024

## Overview

The **War Thunder Camouflage Installer** is a Rust-based desktop application designed to enhance the experience of War Thunder players by allowing them to easily browse, search, and install custom camouflages for their vehicles. The application leverages the power of Rust's GUI library, `eframe` and `egui`, to provide a seamless user interface and experience.


### MAIN WINDOW
![image](https://github.com/user-attachments/assets/c6849b68-156a-4351-912e-c2805a4fb241)

### FILE MENU
![image](https://github.com/user-attachments/assets/6adefb91-cae7-42ba-9726-9794d9353586)

### CUSTOM STRUCTURE POPUP
![image](https://github.com/user-attachments/assets/8de6b3d1-805b-46cb-af68-a6ddb78d7848)

### PAGINATION & INSTALL BUTTONS
![image](https://github.com/user-attachments/assets/79fd6b1a-9ac5-41e6-a21a-4670d5b7bb47)

### CUSTOM TAGGING INPUTS
![image](https://github.com/user-attachments/assets/ba4fb676-3fa0-4623-a054-0930bfb118fe)

### SEARCH BAR & TAG FILTERING
![image](https://github.com/user-attachments/assets/295bd8b8-d272-4b05-91ea-77691033fae7)

### ABOUT POPUP
![image](https://github.com/user-attachments/assets/e2e5bfaa-a924-43f7-8a48-3e2001218c58)


## Features

- **Intuitive Search**: Search through the database of camouflages using keywords that match vehicle names, descriptions, or hashtags.
- **Detailed Camouflage Display**: View comprehensive details about each camouflage, including vehicle name, description, images, file size, number of downloads, likes, and post date.
- **Tag Filtering**: Filter search results using customizable tags to refine camouflage selection.
- **Custom Directory Structure**: Define custom installation paths for camouflages using placeholders for directory structures.
- **Asynchronous Image Loading**: Efficiently load and display images associated with camouflages using asynchronous threading to ensure a smooth user experience.
- **One-Click Skin Installation**: Download and unzip selected camouflages directly into the specified War Thunder skins directory with a single click.
- **Import Local Skins**: Import skins from local archives (zip, rar) and install them directly into the game directory.
- **User-Friendly Interface**: Navigate camouflages, perform searches, and manage installations through a clean and straightforward graphical interface.
- **Error Management**: Built-in error handling to gracefully manage issues such as missing database files, network errors, or missing directories.
- **Cache Management**: Efficiently cache and clear camouflage images to optimize performance.

## Prerequisites

To build and run this project, ensure the following are installed on your system:

- **Rust and Cargo**: The Rust programming language and its package manager, Cargo. Install from [rust-lang.org](https://www.rust-lang.org/).
- **SQLite Database**: Ensure a local SQLite database (`war_thunder_camouflages_test.db`) exists in the root directory of the project or specify its path in the source code.
- **Internet Connection**: Required to fetch camouflage images and ZIP files for installation.

## Dependencies

Add these dependencies to your `Cargo.toml` file:

```toml
[dependencies]
eframe = { version = "0.22.0", features = ["persistence"] }
egui = "0.22.0"
rusqlite = { version = "0.29.0", features = ["bundled"] }
ehttp = "0.2.0"
image = "0.24.6"
base64 = "0.21.0"
rfd = "0.9"
zip = "0.5"
reqwest = { version = "0.11", features = ["blocking"] }
tempfile = "3.3"
thiserror = "1.0"
parking_lot = "0.12"
dirs = "5.0"
rayon = "1.5"

[target.'cfg(windows)'.dependencies.winapi]
version = "0.3.9"
features = ["winuser", "windef"]
```

## Building the Project

1. **Clone the Repository**:

    ```bash
    git clone https://github.com/hasnocool/war_thunder_camouflage_installer.git
    cd war_thunder_camouflage_installer
    ```

2. **Build the Project**:

    Use Cargo to build the project in release mode for optimized performance:

    ```bash
    cargo build --release
    ```

    This command will compile the project and generate an executable in the `target/release` directory.

## Running the Application

After building the project, you can run the application using Cargo or directly from the executable:

```bash
cargo run --release
```

Or run the executable directly:

```bash
./target/release/war_thunder_camo_installer
```
Ensure the `war_thunder_camouflages.db` database is in the same directory or update the path in the source code.

## Configuration

- **Database Path**: Ensure the path to the SQLite database (`war_thunder_camouflages.db`) is correct. You can modify this path in the `main()` function within the source code if needed.
- **War Thunder Skins Directory**: Set this directory from within the application to specify where downloaded camouflages should be installed.

## Usage Guide

### Launching the Application

1. **Start the Application**: Run the compiled executable. The application will initialize and connect to the specified SQLite database.
2. **Initialization Messages**: Console outputs will provide status updates, such as successful database connections or errors.




### Searching for Camouflages

1. **Search Bar**: Enter keywords related to vehicle names, descriptions, or hashtags in the search bar.
2. **Search Execution**: Press "Enter" or click the "Search" button to filter camouflages based on the input.
3. **Tag Filters**: Apply tag filters to refine search results based on custom or predefined tags.

### Viewing Camouflage Details

1. **Camouflage Information**: Detailed information about the selected camouflage, including images and metadata, is displayed in the main panel.
2. **Navigation**: Use the "Previous" and "Next" buttons to navigate through different camouflages.

### Installing Camouflages

1. **Select Camouflage**: Choose a camouflage to install by navigating to it.
2. **Set Skins Directory**: Ensure the War Thunder skins directory is set using the "Browse" button.
3. **Install Camouflage**: Click the "Install" button to download and extract the camouflage ZIP file directly to the specified directory.

### Managing War Thunder Skins Directory

1. **Setting the Directory**: Use the "Browse" button in the application to select or update the War Thunder skins directory.
2. **Directory Path**: Ensure the correct path is displayed and recognized by the application before installing skins.

### Importing Local Skins

1. **Select Directory**: Use the "Import Local Skin" option to select a directory containing skin archives.
2. **Import Skins**: Click "Import" to extract and install the selected skins into the War Thunder skins directory.

### Custom Directory Structure

1. **Define Structure**: Set a custom directory structure for skin installations using placeholders like `%USERSKINS`, `%NICKNAME`, `%SKIN_NAME`, and `%VEHICLE`.
2. **Enable Custom Structure**: Toggle the option to use the custom directory structure within the application settings.

## Error Handling and Troubleshooting

- **Database Errors**: If the database file is missing or corrupted, an error message will be displayed. Ensure the correct database file exists in the specified path.
- **Network Errors**: If there are issues downloading images or ZIP files, the application will display error messages. Check your internet connection or the validity of the URLs.
- **File System Errors**: If there are issues writing to the War Thunder skins directory, ensure you have the necessary permissions and that the directory exists.
- **Cache Issues**: Clear the cache if image loading or display issues occur.

## Contributing

Contributions are welcome! Please follow these steps to contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/YourFeature`).
3. Make your changes and commit them (`git commit -am 'Add YourFeature'`).
4. Push to the branch (`git push origin feature/YourFeature`).
5. Open a pull request.

Please ensure your code adheres to Rust's best practices and is properly formatted using `cargo fmt`.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Acknowledgments

- This application utilizes the `eframe` and `egui` libraries for its graphical user interface.
- Special thanks to the developers and contributors of the Rust crates used in this project: `rusqlite`, `image`, `reqwest`, `rfd`, `tempfile`, `zip`, `thiserror`, `parking_lot`, `dirs`, and `rayon`.

