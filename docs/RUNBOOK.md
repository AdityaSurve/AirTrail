# AirTrail Deployment Runbook
**A step-by-step, plain-English guide to launching the AirTrail Analytics Platform.**

This guide assumes you are starting from scratch and do not have deep programming knowledge. Please follow every step sequentially.

---

## Part 1: Prerequisites (What you need installed)
Before we start, you must install the following software on your computer (if you are on Windows/Mac):
1. **Docker Desktop:** Go to [docker.com](https://www.docker.com/products/docker-desktop/), download, and install it. Open the application and leave it running in the background.
2. **Python:** Go to [python.org](https://www.python.org/downloads/), download Python 3.11 or newer, and verify it is installed. *(Important: During installation on Windows, check the box that says "Add Python to PATH" before hitting install)*.
3. **Git:** Go to [git-scm.com](https://git-scm.com/downloads) and install it with default settings.

---

## Part 2: Running AirTrail Locally (On Your Own Computer)

This is how you get the application running on your personal machine to test it out.

### Step 1: Open the Terminal
* **Windows:** Press `Windows Key`, type `cmd`, and press Enter.
* **Mac:** Press `Cmd + Space`, type `Terminal`, and press Enter.

### Step 2: Navigate to the Project Folder
Use the `cd` command to enter your project folder.
```bash
cd path/to/your/AirTrail/Folder
```
*(Tip: Type `cd `, then drag and drop the folder from your file explorer into the terminal window, then hit Enter).*

### Step 3: Start the Backend Systems (Database, Queues, Storage)
We need to turn on our "servers" which are running virtually inside Docker Desktop. 
By utilizing Docker, the Database itself, the User (`airtrail`), and the Password (`password`) are **automatically created for you** when you run the command below. You do not need to manually configure SQL.

Copy and paste this command, then hit Enter:
```bash
docker compose up -d postgres rabbitmq redis minio
```
**Wait 15 seconds** after running this. Postgres needs time to configure itself under the hood.

**Important (Windows):** If you also installed **PostgreSQL from postgresql.org**, it often listens on **port 5432**—the same port Docker maps for Postgres. Your tools (`alembic`, `seed.py`) use `localhost:5432` by default, so you may be talking to **Windows PostgreSQL**, not the Docker **PostGIS** container. Either **stop the Windows “postgresql” service** (open `services.msc`, stop PostgreSQL) so Docker owns port 5432, or keep using native Postgres and install **PostGIS** for that server (see below).

**Manually Creating the Database Locally (If you are NOT using Docker for the database):**
AirTrail uses **geographic columns**, so the server must support **PostGIS** (not plain PostgreSQL alone).

* **Windows:** After installing PostgreSQL, run **Stack Builder** (installed with PostgreSQL), select your server, and install **PostGIS** for the **same major version** as your PostgreSQL (e.g. 15.x with PostgreSQL 15).
* **Mac (Homebrew):** e.g. `brew install postgis` and follow Homebrew’s notes for enabling the extension.

Then create the database before running Step 4. Open your terminal and run these exact commands:
```bash
psql -U postgres -c "CREATE USER airtrail WITH PASSWORD 'password';"
psql -U postgres -c "CREATE DATABASE airtrail;"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE airtrail TO airtrail;"
psql -U postgres -c "ALTER DATABASE airtrail OWNER TO airtrail;"
psql -U postgres -d airtrail -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```
On PostgreSQL 15+, the `ALTER DATABASE` line avoids `permission denied for schema public` during `alembic upgrade head`. If you prefer not to change the database owner, use `psql -U postgres -d airtrail -c "GRANT ALL ON SCHEMA public TO airtrail;"` instead. The `CREATE EXTENSION postgis` line requires PostGIS to be installed on that machine (see Stack Builder on Windows).

*(If you get a 'psql is not recognized' error on Windows, ensure the `C:\Program Files\PostgreSQL\<version>\bin` folder is added to your computer's PATH environment variables).*

### Step 4: Install Python Tools and Setup the Database
We need to load our database with the correct structure and dummy data, but first we must ensure our Python environment is ready.

**For Windows Users:**
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python packages\airtrail_core\seed.py
```

**For Mac/Linux Users:**
```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
alembic upgrade head
python3 packages/airtrail_core/seed.py
```

### Step 5: Start the Actual Application
Now that our tools and data are ready, let's start the API, the background workers, and the web app.
Run this command:
```bash
docker compose up -d --build api worker dashboard
```
*(This may take a few minutes the very first time as it downloads the necessary files).*

### Step 6: Open AirTrail
Everything is running! Open your internet browser (Chrome, Edge, Safari) and go to:
* **The Dashboard (Where you interact):** [http://localhost:8501](http://localhost:8501)
* **The Storage Console (Where files are saved):** [http://localhost:9001](http://localhost:9001) *(Use `minioadmin` for both username and password)*.

---

## Part 3: Deploying to Cloud Virtual Machines (For Course Deliverables)

For your course, you need to prove the system works across 4 distinct cloud computers (Node 1, Node 2, Node 3, Node 4). Here is exactly how you handle that scenario. 

*(Assume you have SSH access into 4 separate Ubuntu/Linux servers provided by your course instructor).*

### General Setup (Do this on ALL 4 Nodes first)
Log into each node and install Docker and Git.
```bash
sudo apt update
sudo apt install -y docker.io docker-compose git python3-venv
sudo systemctl enable --now docker
```

---

### Node 1: The Database Server
*Log into Node 1.*
1. Clone your project code.
   ```bash
   git clone <YOUR-GITHUB-REPO-URL> AirTrail
   cd AirTrail
   ```
2. Start the database. By utilizing Docker, the user (`airtrail`), password (`password`), and database (`airtrail`) are natively created for you automatically upon running the following:
   ```bash
   sudo docker-compose up -d postgres
   ```

**Manually Creating the Database (If avoiding Docker):**
If you choose to install PostgreSQL natively without Docker, you must explicitly create the user and database yourself. Assuming PostgreSQL is installed:
1. Enter the postgres prompt: `sudo -u postgres psql`
2. Create the user: `CREATE USER airtrail WITH PASSWORD 'password';`
3. Create the database: `CREATE DATABASE airtrail;`
4. Grant privileges: `GRANT ALL PRIVILEGES ON DATABASE airtrail TO airtrail;`
5. **PostgreSQL 15+:** database grants do not allow creating objects in `public` by default. As the superuser, run: `ALTER DATABASE airtrail OWNER TO airtrail;` (recommended), or after `\c airtrail` run: `GRANT ALL ON SCHEMA public TO airtrail;`
6. Connect to the database: `\c airtrail`
7. Add the PostGIS spatial extensions: `CREATE EXTENSION postgis;`
8. Exit the prompt: `\q`

---

### Node 2: Message Brokers (RabbitMQ & Redis)
*Log into Node 2.*
1. Clone your project code.
   ```bash
   git clone <YOUR-GITHUB-REPO-URL> AirTrail
   cd AirTrail
   ```
2. Start the queues and caches.
   ```bash
   sudo docker-compose up -d rabbitmq redis
   ```

---

### Node 3: Backend Processing Workers
*Log into Node 3.*
1. Clone your project code.
   ```bash
   git clone <YOUR-GITHUB-REPO-URL> AirTrail
   cd AirTrail
   ```
2. **CRITICAL STEP:** We must tell the Worker how to connect to Node 1 and Node 2.
   Open the `.env` file using a text editor (like `nano .env`) and replace `localhost` or `postgres` with the **internal IP addresses** of Node 1 and Node 2.
   ```env
   DATABASE_URL=postgresql://airtrail:password@<NODE-1-INTERNAL-IP>:5432/airtrail
   CELERY_BROKER_URL=amqp://guest:guest@<NODE-2-INTERNAL-IP>:5672//
   REDIS_URL=redis://<NODE-2-INTERNAL-IP>:6379/0
   ```
3. Set up the database structure (Migrations).
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   alembic upgrade head
   python packages/airtrail_core/seed.py
   ```
4. Start the worker system.
   ```bash
   sudo docker-compose up -d --build worker
   ```

---

### Node 4: The Public Facing Web App & API
*Log into Node 4.*
1. Clone your project code.
   ```bash
   git clone <YOUR-GITHUB-REPO-URL> AirTrail
   cd AirTrail
   ```
2. Similarly to Node 3, edit your `.env` file!
   ```bash
   nano .env
   ```
   Provide the IP addresses of Node 1, Node 2, and whichever Node gets MinIO storage.
   ```env
   DATABASE_URL=postgresql://airtrail:password@<NODE-1-INTERNAL-IP>:5432/airtrail
   CELERY_BROKER_URL=amqp://guest:guest@<NODE-2-INTERNAL-IP>:5672//
   REDIS_URL=redis://<NODE-2-INTERNAL-IP>:6379/0
   ```
3. Start the UI and API.
   ```bash
   sudo docker-compose up -d --build api dashboard minio
   ```
4. Access the web app using Node 4's **Public IP address**!
   Go to: `http://<NODE-4-PUBLIC-IP>:8501`

---

## Common Troubleshooting
* **"role airtrail does not exist" Error when running alembic upgrades:**
  Usually either (a) **Docker Postgres** did not initialize correctly (stale volume), or (b) **`alembic` is connecting to a different Postgres** than you think (e.g. a native Windows install on port 5432 instead of the container). Our `docker-compose.yml` sets `POSTGRES_USER: airtrail`, so inside the container the superuser is **`airtrail`**, not `postgres`.

  **If you intend to use Docker Postgres:** wipe the volume and bring Postgres back up so init scripts create `airtrail` / `airtrail`:
  1. `docker compose down`
  2. `docker volume rm airtrail_postgres_data`
  3. `docker compose up -d postgres`
  4. Wait ~15 seconds, then run `alembic upgrade head` again.

  **If you are using native PostgreSQL** (you can use `psql -U postgres` on the host): create the role and database as in *Manually Creating the Database*, then apply the **PostgreSQL 15+** schema step there so migrations can create tables.

* **"permission denied for schema public" when running `alembic upgrade head`:**  
  On PostgreSQL 15+, the `public` schema no longer allows arbitrary `CREATE` for non-owners. As a superuser (e.g. `postgres` on a native install), run either:
  ```bash
  psql -U postgres -d airtrail -c "ALTER DATABASE airtrail OWNER TO airtrail;"
  ```
  or:
  ```bash
  psql -U postgres -d airtrail -c "GRANT ALL ON SCHEMA public TO airtrail;"
  ```
  Then run `alembic upgrade head` again.

  **Inside Docker** (this repo’s compose), connect as `airtrail` and you should not need this unless you manually created a second user:
  ```bash
  docker exec -it airtrail-postgres-1 psql -U airtrail -d airtrail -c "GRANT ALL ON SCHEMA public TO some_other_role;"
  ```
  *(Replace `airtrail-postgres-1` with your container name from `docker ps` if different.)*

* **`extension "postgis" is not available`** (often with a path like `C:/Program Files/PostgreSQL/.../postgis.control` **No such file**):  
  Migrations are running against **native PostgreSQL without PostGIS**. Fix one of these ways:
  1. **Prefer Docker:** Stop the Windows PostgreSQL service so `localhost:5432` is the **Docker** `postgis/postgis` container (from Step 3), then run `alembic upgrade head` again.
  2. **Stay on native Postgres:** Install **PostGIS** for your PostgreSQL version (Windows: **Stack Builder** → PostGIS), then in the `airtrail` database run `CREATE EXTENSION postgis;`, then `alembic upgrade head` again.
