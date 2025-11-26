# Crear las carpetas dentro del servidor
- Crear carpeta del proyecto
  ```bash
  mkdir proyecto_invernadero
  ```
  ```bash
  cd proyecto_invernadero
  ```

- Crear entorno virtual 
  ```bash
  sudo apt install python3-venv -y
  ```
  ```bash
  python3 -m venv venv
  ```
  ```bash
  source venv/bin/activate
  ```

- Instalar pip y python3
  ```bash
  sudo apt update
  ```
  ```bash
  sudo apt install python3 python3-pip -y
  ```
- Instalar Flask 
  ```bash
  pip3 install Flask 
  ```
- Librerías necesarias
  ```bash
  pip install flask flask_socketio pymongo requests eventlet
  ```

  # Tutorial de instalacion de MongoDB en el servidor (Recordar hacerlo en el entorno virtual del proyecto)

- **1 mongoDB**:

  - 1.1 Ver la version de Ubuntu (Si es Noble, Jammy o Focal)

    ```bash
    cat /etc/lsb-release
    ```
  - 1.2 Importar la public key oficial de mongo

    ```bash
    sudo apt-get install gnupg curl
    ``` 
  - 1.3 MongoDB public GPG key
    ```bash
    curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc | \
    sudo gpg -o /usr/share/keyrings/mongodb-server-8.0.gpg \
    --dearmor
    ```
    
  - 1.4 Create the list file.
     ```bash
    /etc/apt/sources.list.d/mongodb-org-8.0.list
    ``` 
  - 1.5 Dependiendo de la version de ubuntu escojer una
    - Noble
      ```bash
      echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] https://repo.mongodb.org/apt/ubuntu noble/mongodb-org/8.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-8.0.list
      ```
    - Jammy
      ```bash
      echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/8.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-8.0.list
      ```
    - Focal
      ```bash
      echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/8.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-8.0.list
      ```

  - 1.6 Reload the package database
    ```bash
    sudo apt-get update
    ```  
  - 1.7 Install MongoDB Community Server.
    ```bash
    sudo apt-get install -y mongodb-org
    ``` 
  - 1.8 Start MongoDB.
    ```bash
    sudo systemctl start mongod
    ``` 
  - 1.9 Verify that MongoDB has started successfully (para salir del status apretar la tecla "q").
    ```bash
    sudo systemctl status mongod
    ``` 
  - 1.10 Para que mongo se inicie automaticamente cuando inicias el servidor usa este comando
    ```bash
    sudo systemctl enable mongod
    ```

- 2 Flask-CORS y PyMongo
  ```bash
    pip3 install flask-cors pymongo
  ```



# Arduino

## Librerias que deben importarse
```bash
SparkFun SHTC3
Adafruit VEML7700
ArduinoJson
Light_VEML7700 (la versión de RAKwireless VEML Light Sensor)
```
- Luego copiamos el codigo del repositorio

# Página Web
```bash
mkdir templates
```
```bash
nano templates/index.html
```
- Luego compiar el codigo del index.html


