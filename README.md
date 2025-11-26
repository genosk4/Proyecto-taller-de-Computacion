# Indicaciones para crear el proyecto 

## Crear las carpetas dentro del servidor AWS
- Crear carpeta del proyecto
  ```bash
  mkdir proyecto_invernadero
  ```
  ```bash
  cd proyecto_invernadero
  ```
- Instalar pip y python3
  ```bash
  sudo apt update
  ```
  ```bash
  sudo apt install python3 python3-pip -y
  ```
  
- Instalar y Crear entorno virtual 
  ```bash
  sudo apt install python3-venv -y
  ```
  ```bash
  python3 -m venv venv
  ```
  ```bash
  source venv/bin/activate
  ```
  
- Instalar Flask 
  ```bash
  pip3 install Flask 
  ```
  
- Librerías necesarias
  ```bash
  pip install flask flask_socketio pymongo requests eventlet
  ```

- Crear archivo app.py donde se encontrara el codigo para el servidor de nuestro proyecto
  ```bash
  nano app.py
  ```
  - Dentro pegar el contenido del archivo app.py del repositorio

  

## Tutorial de instalacion de MongoDB en el servidor (dentro del entorno virtual del proyecto)

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

## Arduino (PC local)

- Librerias que deben importarse:
  
   - 1.- Sensor de Temperatura y Humedad
      ```bash
      SparkFun SHTC3
      ```
   - 2.- Sensor de Luz
      ```bash
      RAKwireless VEML Light Sensor
      ```
   - 3.- Para poder gestionar archivos JSON
      ```bash
      ArduinoJson
      ```
   - 4.- Otra librería para el sensor de luz en caso de que la primera de problemas (no debería ser necesaria)
      ```bash
      Adafruit VEML7700
      ```
- Luego copiamos el codigo .cpp del repositorio
 
- En caso de que el codigo de error y diga algo relacionao con Python, ejecutar estos comandos en la consola
  ```bash
    sudo apt update
  ```
  ```bash
    sudo apt install python-is-python3
  ```
    
## Página Web (Dentro de AWS)
- Crear una carpeta llamada templates en la carpeta del proyecto y dentro de esta crear un archivo index.html
  ```bash
  mkdir templates
  ```
  ```bash
  nano templates/index.html
  ```
- Luego copiar el codigo del index.html

## Aplicación movil en Adroid Studio 
- Crear un proyecto eligiendo el modelo Empty Views Activity
- Luego compiar los archivos del repositorio de la rama **Android**

