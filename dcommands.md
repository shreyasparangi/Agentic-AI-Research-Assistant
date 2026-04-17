Open a single terminal in your root folder and run this command to build the images and spin up the entire architecture in detached mode:

Bash
docker-compose up -d --build
Docker will download the OS images, install your Python and Node packages, and boot up both servers.

Your UI will be live at http://localhost:3000

Your API will be live at http://localhost:8000

When the expo is over or you want to shut the engines down cleanly, simply run:

Bash
docker-compose down