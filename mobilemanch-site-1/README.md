# MobileManch Site

## Overview
MobileManch is a Pakistan-focused platform for smartphone reviews, comparisons, and the best deals. It provides concise, practical information to help users compare mobile devices.

## GSMArena importer

Install the importer dependency:

```bash
python -m pip install -r requirements.txt
```

Import a public GSMArena phone page into `data/gsmarena_mobiles.json` and both static site entry points:

```bash
python tools/import_gsmarena.py https://www.gsmarena.com/samsung_galaxy_a56-13662.php
```

The importer saves specifications, image metadata, source URL, and a review link. It does not copy the full review article. Check GSMArena's terms and `robots.txt`, use a reasonable delay, and verify Pakistan pricing locally before publishing.

## Project Structure
```
mobilemanch-site
├── index.html          # Main HTML document for the MobileManch site
├── assets
│   ├── css
│   │   └── styles.css  # CSS styles for the site
│   └── js
│       └── main.js     # JavaScript functionality for the site
└── README.md           # Documentation for the project
```

## Setup Instructions
1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd mobilemanch-site
   ```

2. **Open the Project**
   Open the `index.html` file in your preferred web browser to view the site.

3. **Styles**
   The styles for the site are located in `assets/css/styles.css`. You can modify this file to change the appearance of the site.

4. **JavaScript**
   Any JavaScript functionality can be added to `assets/js/main.js`. This file is currently empty but can be used to enhance interactivity.

## Features
- Latest smartphone reviews
- Comparison of different mobile devices
- User-friendly interface
- Responsive design for mobile and desktop users
- Daily GSMArena news updates through GitHub Actions

## Daily news automation

The root `update_site.py` fetches the latest ten GSMArena news titles, links, and images into `updates.json`. The workflow at `.github/workflows/daily_update.yml` runs daily at 04:00 UTC and can also be started manually from the Actions tab.

The workflow requests `contents: write` permission and commits only when `updates.json` changes. If GitHub repository settings override workflow permissions, enable **Settings > Actions > General > Workflow permissions > Read and write permissions**.

## Contributing
Contributions are welcome! Please feel free to submit a pull request or open an issue for any suggestions or improvements.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.