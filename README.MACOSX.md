![DALL·E 2024-09-08 16 56 56 - A logo for War Thunder Camouflage Installer v1 0 0 highlighting support for macOS Big Sur  The design should incorporate elements of both military cam](https://github.com/user-attachments/assets/6f4df01d-cc28-4f3e-98b4-79a42dcacfbd)

# War Thunder Camouflage Installer v1.0.0 - macOS Big Sur Edition

Welcome to the **macOS Big Sur** version of the **War Thunder Camouflage Installer**! This README is specifically for Mac users and will guide you through the installation and usage of the app on your macOS system.

---

### macOS Big Sur Announcement

We are proud to announce that the **War Thunder Camouflage Installer v1.0.0** is fully compatible with **macOS Big Sur**! Enjoy the same streamlined experience, now optimized for macOS, with easy camouflage installation for War Thunder.

---

### Screenshot of War Thunder Camouflage Installer on macOS Big Sur
![Screen Shot 2024-09-08 at 3 12 15 PM](https://github.com/user-attachments/assets/7c25d499-499e-465c-a1d0-98c61c0713a5)

---

## How to Install the War Thunder Camo Installer on macOS

Follow these simple steps to install and run the **War Thunder Camouflage Installer** on your macOS system:

### Step 1: Download the App

Go to the **Releases** section and download the latest macOS version of the app. You can find it here:
[Download War Thunder Camouflage Installer for macOS Big Sur](https://github.com/hasnocool/war_thunder_camouflage_installer/releases/download/v2024.09.06-002351/war_thunder_camo_installer_osx_bigsur)

Additionally, download the `war_thunder_camouflages.db` file, which contains the camouflage data.

### Step 2: Move Files to the Same Folder

After downloading, make sure both the application file and the `war_thunder_camouflages.db` file are stored in the **same folder** on your Mac.

This is very important! If these files are not in the same folder, the app won't be able to find the database.

### Step 3: Run the App

1. **Open the App**: Locate the app file you downloaded, right-click, and select **Open** to bypass macOS security warnings.
2. **Set the Database**: The database does not load automatically yet, so you need to set it manually:
   - Navigate to the **File** menu and choose **Set Database Location**.
   - Select the `war_thunder_camouflages.db` file from the folder where you downloaded it.
   
Once the app is running and the database is set, you're ready to start using the War Thunder Camouflage Installer!

---

## Configuration on macOS

* **Database Path**: Ensure the `war_thunder_camouflages.db` file is in the same directory as the app. You will need to manually set the database location each time you run the app until automatic loading is available.
* **War Thunder Skins Directory**: Use the app to set the directory where you want your camouflages to be installed. The app will guide you through this process.

---

## Usage Guide for macOS

### Launching the Application

1. **Start the Application**: Open the app by double-clicking it or right-clicking and choosing **Open**.
2. **Setting the Database**: After launching, go to the **File** menu and manually set the database location.
3. **Initialization**: You'll see messages confirming that the database is connected if everything is set correctly.

### Searching for Camouflages

1. **Search Bar**: Enter the name of a vehicle or some relevant keywords in the search bar.
2. **Press Enter**: Hit “Enter” or click the **Search** button to view a list of matching camouflages.
3. **Tag Filters**: Use filters to narrow down your search results if you're looking for something specific.

### Viewing Camouflage Details

1. **Camouflage Info**: Click on a camouflage to see its details, including images.
2. **Navigation**: Use "Previous" and "Next" buttons to browse through camouflages.

### Installing Camouflages

1. **Select a Camouflage**: Choose the camouflage you like by clicking on it.
2. **Set the Skins Directory**: Use the **Browse** button to select the directory where you want the camouflage installed.
3. **Install**: Click the **Install** button, and the app will install the camouflage for you.

### Managing the Skins Directory

1. **Set the Directory**: Update the skins directory at any time by clicking the **Browse** button and selecting a new folder.
2. **Check Directory Path**: Always ensure the correct directory path is displayed before installing.

### Importing Local Skins

1. **Select Directory**: Use the **Import Local Skin** option to import camouflages you've saved locally.
2. **Import**: Click **Import** to add these skins to your War Thunder installation.

---

## Error Handling on macOS

* **Database Not Loaded**: Ensure the `.db` file is in the same folder as the app. Manually set the database through the **File** menu if it doesn't load.
* **Internet Issues**: Check your internet connection if the app cannot download skins.
* **Permission Problems**: If you experience issues with file permissions, make sure you have write access to the skins directory.

---

## Contributing

If you'd like to contribute to the project, follow these steps:

1. Fork this repository.
2. Create a new branch (`git checkout -b feature/YourFeature`).
3. Make your changes and commit them (`git commit -am 'Add YourFeature'`).
4. Push your branch (`git push origin feature/YourFeature`).
5. Open a pull request, and we'll review it!

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more information.

---

## Acknowledgments

A huge thanks to everyone who helped make this project possible! Special recognition to the libraries used, including `eframe`, `egui`, `rusqlite`, and others.
