![logo-v1 0 0](https://github.com/user-attachments/assets/fc11aa67-cc24-43ea-8826-7bfc90e58f09)


![Screen Shot 2024-09-08 at 3 12 15 PM](https://github.com/user-attachments/assets/7c25d499-499e-465c-a1d0-98c61c0713a5)


## How to Install the War Thunder Camo Installer

Hey there! If you're new to this, don't worry, I've got you. Here’s how to get everything up and running. Follow these steps carefully, just like we’re putting together a puzzle!

### Step 1: Go to the Release Section

First, go to the **Releases** section of this repository. You’ll find it at the top of the GitHub page under the **Code** tab. Just look for the latest version of the app.

### Step 2: Download the Files

In the **Releases** section, you'll see two files you need:
1. The `.exe` file (this is the app).
2. The `.db` file (this is the database that holds all the camouflage data).

### Step 3: Put Them Together

Once you’ve downloaded these two files, make sure they are **in the same folder** on your computer. 

This part is very important! If they’re not in the same folder, the app won’t be able to find the database, and it will get confused. Think of the `.exe` and `.db` as best friends – they need to be together!

### Step 4: Run the App

To start the app, simply double-click the `.exe` file. It will open up, and it should automatically connect to the database.

If everything is in the right place, you’re good to go!

### Step 5: Install Some Cool Skins!

Once the app is running, you can use it to search for, view, and install awesome War Thunder camouflages. Just follow the on-screen instructions, and you’ll have cool new skins in no time!

---

## Configuration

* **Database Path**: Make sure the `war_thunder_camouflages.db` file is in the same directory as the executable file. If it's not, the app won’t work correctly.
* **War Thunder Skins Directory**: In the app, you can set the folder where you want the camouflages to be installed. Don’t worry – the app will guide you through it!

## Usage Guide

### Launching the Application

1. **Start the Application**: Run the `.exe` file by double-clicking it.
2. **Initialization Messages**: You’ll see some messages on your screen that tell you if everything is set up correctly. If it says the database is connected, you’re ready!

### Searching for Camouflages

1. **Search Bar**: Type the name of a vehicle or some keywords into the search bar.
2. **Press Enter**: Hit the “Enter” key or click the “Search” button to see a list of camouflages that match your search.
3. **Tag Filters**: Use filters to narrow down the results if you’re looking for something specific.

### Viewing Camouflage Details

1. **Camouflage Info**: You’ll see images and details about the camouflage you selected.
2. **Navigation**: Click "Previous" or "Next" to browse through different camouflages.

### Installing Camouflages

1. **Select a Camouflage**: Pick a camouflage you like by clicking on it.
2. **Set Skins Directory**: Use the “Browse” button to choose the folder where you want the camouflage installed.
3. **Install**: Hit the "Install" button, and the app will take care of the rest!

### Managing War Thunder Skins Directory

1. **Set Directory**: You can update the skins directory anytime by clicking the "Browse" button and choosing a new folder.
2. **Check Directory Path**: Always make sure the correct path is shown before installing.

### Importing Local Skins

1. **Select Directory**: Use the "Import Local Skin" option to select a folder where you’ve stored camouflages.
2. **Import**: Click "Import" to add those skins to your War Thunder skins folder.

---

## Error Handling

* **Database Missing**: If the app says the database is missing, make sure the `.db` file is in the same folder as the `.exe` file.
* **Internet Issues**: If it can’t download skins, check your internet connection.
* **Permission Problems**: If it can't install the skins, make sure you have permission to write files to the skins directory.

---

## Contributing

Want to help out? Awesome! Here's how:

1. Fork this repository.
2. Create a new branch (`git checkout -b feature/YourFeature`).
3. Make your changes, then commit them (`git commit -am 'Add YourFeature'`).
4. Push to your branch (`git push origin feature/YourFeature`).
5. Open a pull request, and we’ll review it!

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

Big thanks to everyone who made this project possible! Special shout-out to the libraries used: `eframe`, `egui`, `rusqlite`, and more.
