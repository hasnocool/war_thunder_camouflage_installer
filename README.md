Here is the updated README in Markdown format:

# War Thunder Camouflage Installer
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

* **Database Path**: Ensure the path to the SQLite database (`war_thunder_camouflages.db`) is correct. You can modify this path in the `main()` function within the source code if needed.
* **War Thunder Skins Directory**: Set this directory from within the application to specify where downloaded camouflages should be installed.

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

* **Database Errors**: If the database file is missing or corrupted, an error message will be displayed. Ensure the correct database file exists in the specified path.
* **Network Errors**: If there are issues downloading images or ZIP files, the application will display error messages. Check your internet connection or the validity of the URLs.
* **File System Errors**: If there are issues writing to the War Thunder skins directory, ensure you have the necessary permissions and that the directory exists.
* **Cache Issues**: Clear the cache if image loading or display issues occur.

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

* This application utilizes the `eframe` and `egui` libraries for its graphical user interface.
* Special thanks to the developers and contributors of the Rust crates used in this project: `rusqlite`, `image`, `reqwest`, `rfd`, `tempfile`, `zip`, `thiserror`, `parking_lot`, `dirs`, and `rayon`.